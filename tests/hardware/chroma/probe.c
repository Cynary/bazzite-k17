// Offline HEVC hardware-decode and libplacebo import/render probe.
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/hwcontext.h>
#include <libavutil/hwcontext_drm.h>
#include <libavutil/hwcontext_vaapi.h>
#include <libavutil/pixdesc.h>
#include <libplacebo/renderer.h>
#include <libplacebo/utils/libav.h>
#include <libplacebo/vulkan.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
static double now(void) {
  struct timespec t;
  clock_gettime(CLOCK_MONOTONIC, &t);
  return t.tv_sec + t.tv_nsec * 1e-9;
}
static enum AVPixelFormat pick(AVCodecContext *c, const enum AVPixelFormat *f) {
  (void)c;
  for (; *f != AV_PIX_FMT_NONE; f++)
    if (*f == AV_PIX_FMT_VAAPI)
      return *f;
  return AV_PIX_FMT_NONE;
}
#define CHECK(x)                                                               \
  do {                                                                         \
    if (!(x)) {                                                                \
      fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x);                     \
      exit(2);                                                                 \
    }                                                                          \
  } while (0)
static bool next_frame(AVCodecContext *dec, AVFormatContext *in, int si,
                       AVPacket *pkt, AVFrame *f) {
  for (;;) {
    int ret = avcodec_receive_frame(dec, f);
    if (ret == AVERROR_EOF)
      return false;
    if (ret >= 0)
      return true;
    CHECK(ret == AVERROR(EAGAIN));
    int r;
    for (;;) {
      r = av_read_frame(in, pkt);
      if (r < 0 || pkt->stream_index == si)
        break;
      av_packet_unref(pkt);
    }
    CHECK(r >= 0 || r == AVERROR_EOF);
    CHECK(avcodec_send_packet(dec, r < 0 ? NULL : pkt) >= 0);
    av_packet_unref(pkt);
  }
}
struct queue {
  AVCodecContext *dec;
  AVFormatContext *in;
  int si, limit, head, count;
  bool done;
  AVFrame *frames[3];
  pthread_mutex_t mutex;
  pthread_cond_t changed;
};
static void *produce(void *opaque) {
  struct queue *q = opaque;
  AVPacket *pkt = av_packet_alloc();
  AVFrame *frame = av_frame_alloc();
  for (int n = 0; n < q->limit; n++) {
    if (!next_frame(q->dec, q->in, q->si, pkt, frame))
      break;
    pthread_mutex_lock(&q->mutex);
    while (q->count == 3)
      pthread_cond_wait(&q->changed, &q->mutex);
    q->frames[(q->head + q->count) % 3] = av_frame_clone(frame);
    CHECK(q->frames[(q->head + q->count) % 3]);
    q->count++;
    pthread_cond_signal(&q->changed);
    pthread_mutex_unlock(&q->mutex);
    av_frame_unref(frame);
  }
  av_frame_free(&frame);
  av_packet_free(&pkt);
  pthread_mutex_lock(&q->mutex);
  q->done = true;
  pthread_cond_signal(&q->changed);
  pthread_mutex_unlock(&q->mutex);
  return NULL;
}
static bool consume(struct queue *q, AVFrame *frame) {
  pthread_mutex_lock(&q->mutex);
  while (!q->count && !q->done)
    pthread_cond_wait(&q->changed, &q->mutex);
  if (!q->count) {
    pthread_mutex_unlock(&q->mutex);
    return false;
  }
  AVFrame **slot = &q->frames[q->head];
  av_frame_move_ref(frame, *slot);
  av_frame_free(slot);
  q->head = (q->head + 1) % 3;
  q->count--;
  pthread_cond_signal(&q->changed);
  pthread_mutex_unlock(&q->mutex);
  return true;
}

int main(int argc, char **argv) {
  CHECK(argc >= 3);
  int mode = atoi(argv[2]), limit = argc > 3 ? atoi(argv[3]) : 600;
  AVFormatContext *in = NULL;
  CHECK(avformat_open_input(&in, argv[1], NULL, NULL) >= 0);
  CHECK(avformat_find_stream_info(in, NULL) >= 0);
  int si = av_find_best_stream(in, AVMEDIA_TYPE_VIDEO, -1, -1, NULL, 0);
  CHECK(si >= 0);
  AVCodecContext *dec = avcodec_alloc_context3(
      avcodec_find_decoder(in->streams[si]->codecpar->codec_id));
  CHECK(dec);
  CHECK(avcodec_parameters_to_context(dec, in->streams[si]->codecpar) >= 0);
  if (mode != 3) {
    CHECK(av_hwdevice_ctx_create(&dec->hw_device_ctx, AV_HWDEVICE_TYPE_VAAPI,
                                 "/dev/dri/renderD128", NULL, 0) >= 0);
    dec->get_format = pick;
  }
  dec->thread_count = 1;
  CHECK(avcodec_open2(dec, dec->codec, NULL) >= 0);
  pl_log log = pl_log_create(
      PL_API_VER, pl_log_params(.log_cb = pl_log_simple, .log_priv = stderr,
                                .log_level = PL_LOG_INFO));
  pl_vulkan vk = NULL;
  pl_renderer rr = NULL;
  pl_tex target = NULL, cache[4] = {0};
  if (mode) {
    vk = pl_vulkan_create(log, NULL);
    CHECK(vk);
    rr = pl_renderer_create(log, vk->gpu);
    CHECK(rr);
  }
  AVPacket *pkt = av_packet_alloc();
  AVFrame *f = av_frame_alloc();
  int count = 0;
  CHECK(mode >= 0 && mode <= 5 && limit > 0);
  struct queue queue = {.dec = dec,
                        .in = in,
                        .si = si,
                        .limit = limit,
                        .mutex = PTHREAD_MUTEX_INITIALIZER,
                        .changed = PTHREAD_COND_INITIALIZER};
  pthread_t worker;
  double start = now(), sync = 0, map = 0, render = 0;
  if (mode == 5)
    CHECK(pthread_create(&worker, NULL, produce, &queue) == 0);
  while (count < limit) {
    if (!(mode == 5 ? consume(&queue, f) : next_frame(dec, in, si, pkt, f)))
      break;
    double t = now();
    if (mode != 3) {
      AVHWFramesContext *fc = (void *)f->hw_frames_ctx->data;
      AVVAAPIDeviceContext *vc = fc->device_ctx->hwctx;
      // Early-mapping modes synchronize once through av_hwframe_map below.
      // An additional vaSyncSurface here can wait for later reference users.
      if (mode < 4)
        CHECK(vaSyncSurface(vc->display, (VASurfaceID)(uintptr_t)f->data[3]) ==
              VA_STATUS_SUCCESS);
      if (!count) {
        AVFrame *d = av_frame_alloc();
        d->format = AV_PIX_FMT_DRM_PRIME;
        d->hw_frames_ctx = av_buffer_ref(f->hw_frames_ctx);
        CHECK(av_hwframe_map(d, f,
                             AV_HWFRAME_MAP_READ | AV_HWFRAME_MAP_DIRECT) >= 0);
        AVDRMFrameDescriptor *drm = (void *)d->data[0];
        fprintf(stderr, "sw_format=%s layers=%d\n",
                av_get_pix_fmt_name(fc->sw_format), drm->nb_layers);
        for (int j = 0; j < drm->nb_layers; j++) {
          unsigned a = drm->layers[j].format;
          fprintf(stderr, "fourcc=%c%c%c%c modifier=%llx planes=%d\n", a & 255,
                  (a >> 8) & 255, (a >> 16) & 255, a >> 24,
                  (unsigned long long)drm->objects[0].format_modifier,
                  drm->layers[j].nb_planes);
        }
        av_frame_free(&d);
      }
    }
    sync += now() - t;
    if (mode) {
      struct pl_frame image = {0};
      AVFrame *prime = NULL;
      const AVFrame *source = f;
      t = now();
      if (mode == 4 || mode == 5) {
        prime = av_frame_alloc();
        CHECK(prime);
        prime->format = AV_PIX_FMT_DRM_PRIME;
        prime->width = f->width;
        prime->height = f->height;
        prime->hw_frames_ctx = av_buffer_ref(f->hw_frames_ctx);
        CHECK(av_hwframe_map(prime, f,
                             AV_HWFRAME_MAP_READ | AV_HWFRAME_MAP_DIRECT) >= 0);
        CHECK(av_frame_copy_props(prime, f) >= 0);
        source = prime;
      }
      CHECK(pl_map_avframe_ex(
          vk->gpu, &image, pl_avframe_params(.frame = source, .tex = cache)));
      map += now() - t;
      if (mode >= 2) {
        if (!target) {
          pl_fmt fmt = pl_find_named_fmt(vk->gpu, "rgba16hf");
          CHECK(fmt);
          target = pl_tex_create(
              vk->gpu,
              pl_tex_params(.w = f->width, .h = f->height, .format = fmt,
                            .renderable = true, .host_readable = true));
          CHECK(target);
        }
        struct pl_frame out = {.num_planes = 1,
                               .planes = {{.texture = target,
                                           .components = 4,
                                           .component_mapping = {0, 1, 2, 3}}},
                               .repr = {.sys = PL_COLOR_SYSTEM_RGB,
                                        .levels = PL_COLOR_LEVELS_FULL},
                               .color = image.color};
        t = now();
        CHECK(pl_render_image(rr, &image, &out, &pl_render_fast_params));
        pl_gpu_finish(vk->gpu);
        render += now() - t;
        if (count == 0 && argc > 4) {
          size_t size = (size_t)f->width * f->height * 8;
          void *buf = malloc(size);
          CHECK(buf);
          CHECK(pl_tex_download(
              vk->gpu, pl_tex_transfer_params(.tex = target, .ptr = buf)));
          FILE *o = fopen(argv[4], "wb");
          CHECK(o);
          CHECK(fwrite(buf, 1, size, o) == size);
          fclose(o);
          free(buf);
        }
      }
      pl_unmap_avframe(vk->gpu, &image);
      av_frame_free(&prime);
    }
    count++;
    av_frame_unref(f);
  }
  if (mode == 5)
    CHECK(pthread_join(worker, NULL) == 0);
  pthread_mutex_destroy(&queue.mutex);
  pthread_cond_destroy(&queue.changed);
  double elapsed = now() - start;
  printf("frames=%d seconds=%.6f fps=%.3f sync_ms=%.3f map_ms=%.3f "
         "render_ms=%.3f\n",
         count, elapsed, count / elapsed, sync * 1000 / count,
         map * 1000 / count, render * 1000 / count);
  if (vk) {
    pl_gpu_finish(vk->gpu);
    pl_tex_destroy(vk->gpu, &target);
    for (int j = 0; j < 4; j++)
      pl_tex_destroy(vk->gpu, &cache[j]);
    pl_renderer_destroy(&rr);
    pl_vulkan_destroy(&vk);
  }
  pl_log_destroy(&log);
  av_frame_free(&f);
  av_packet_free(&pkt);
  avcodec_free_context(&dec);
  avformat_close_input(&in);
  return count == limit ? 0 : 3;
}
