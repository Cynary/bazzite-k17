// SPDX-License-Identifier: MIT
// VHF device setup follows libvirtualgamepad (c) 2026 Chase Payne, MIT.
// Experimental UMDF/VHF transport. Initialization replies come from hardware;
// firmware updates, pairing and calibration writes are not forwarded.
#define WIN32_NO_STATUS
#include <windows.h>
#undef WIN32_NO_STATUS
#include "descriptor.h"
#include "protocol.h"
#include <cstring>
#include <vhf.h>
#include <wdf.h>
using namespace steam_native;
struct pending {
  VHFOPERATIONHANDLE handle;
  PHID_XFER_PACKET transfer;
  packet request;
  ULONGLONG deadline;
  bool delivered;
};
struct context {
  SRWLOCK lock;
  WDFWAITLOCK lifetime;
  WDFIOTARGET target;
  WDFTIMER timer;
  VHFHANDLE vhf;
  WDFFILEOBJECT owner;
  bool opened, stopping, ready, pumping;
  std::uint64_t next_id;
  pending requests[32];
  packet inputs[256];
  unsigned head, count;
};
WDF_DECLARE_CONTEXT_TYPE_WITH_NAME(context, ctx)
struct guard {
  context *c;
  explicit guard(context *p) : c(p) { AcquireSRWLockExclusive(&c->lock); }
  ~guard() { ReleaseSRWLockExclusive(&c->lock); }
};
void expire(context *c, bool all) {
  VHFOPERATIONHANDLE handles[32]{};
  unsigned n = 0;
  {
    guard g(c);
    const auto now = GetTickCount64();
    for (auto &p : c->requests)
      if (p.handle && (all || now >= p.deadline)) {
        handles[n++] = p.handle;
        p = {};
      }
  }
  for (unsigned i = 0; i < n; i++)
    VhfAsyncOperationComplete(handles[i],
                              all ? STATUS_CANCELLED : STATUS_IO_TIMEOUT);
}
void tick(WDFTIMER t) { expire(ctx(WdfTimerGetParentObject(t)), false); }
void pump(context *c) {
  {
    guard g(c);
    if (c->pumping)
      return;
    c->pumping = true;
  }
  for (;;) {
    packet p{};
    VHFHANDLE h{};
    {
      guard g(c);
      if (c->stopping || !c->vhf || !c->ready || !c->count) {
        c->pumping = false;
        return;
      }
      p = c->inputs[c->head];
      c->head = (c->head + 1) % 256;
      c->count--;
      c->ready = false;
      h = c->vhf;
    }
    HID_XFER_PACKET transfer{p.data, p.size, p.data[0]};
    const auto status = VhfReadReportSubmit(h, &transfer);
    if (!NT_SUCCESS(status)) {
      guard g(c);
      c->pumping = false;
      return;
    }
  }
}
void ready(PVOID ptr) {
  auto *c = static_cast<context *>(ptr);
  {
    guard g(c);
    c->ready = true;
  }
  pump(c);
}
void enqueue(PVOID ptr, VHFOPERATIONHANDLE handle, PHID_XFER_PACKET transfer,
             operation op) {
  auto *c = static_cast<context *>(ptr);
  NTSTATUS status = STATUS_DEVICE_BUSY;
  if (!transfer || !transfer->reportBuffer || !transfer->reportBufferLen ||
      transfer->reportBufferLen > 64) {
    VhfAsyncOperationComplete(handle, STATUS_INVALID_PARAMETER);
    return;
  }
  auto *b = transfer->reportBuffer;
  const auto n = transfer->reportBufferLen;
  bool valid = b[0] == transfer->reportId;
  if (op == operation::get_feature) {
    b[0] = transfer->reportId;
    valid = true;
  }
  if (op == operation::set_feature) {
    valid = valid && n == 64 && (b[0] == 1 || b[0] == 2);
    if (valid && !safe_feature(b[0], b[1], b[2]))
      op = operation::blocked_feature;
  }
  if (op == operation::get_feature)
    valid = valid && n == 64 && (b[0] == 1 || b[0] == 2);
  if (op == operation::write) {
    auto size = output_size(b[0]);
    valid = valid && size && (n == size || n == 64);
  }
  if (!valid) {
    VhfAsyncOperationComplete(handle, STATUS_NOT_SUPPORTED);
    return;
  }
  {
    guard g(c);
    if (c->stopping || !c->owner)
      status = STATUS_DEVICE_NOT_READY;
    else
      for (auto &p : c->requests)
        if (!p.handle) {
          p.handle = handle;
          p.transfer = transfer;
          p.deadline = GetTickCount64() + 2000;
          p.request.id = ++c->next_id;
          p.request.op = op;
          p.request.size = n;
          std::memcpy(p.request.data, b, n);
          return;
        }
  }
  VhfAsyncOperationComplete(handle, status);
}
void get_feature(PVOID c, VHFOPERATIONHANDLE h, PVOID, PHID_XFER_PACKET t) {
  enqueue(c, h, t, operation::get_feature);
}
void set_feature(PVOID c, VHFOPERATIONHANDLE h, PVOID, PHID_XFER_PACKET t) {
  enqueue(c, h, t, operation::set_feature);
}
void write_report(PVOID c, VHFOPERATIONHANDLE h, PVOID, PHID_XFER_PACKET t) {
  enqueue(c, h, t, operation::write);
}
// Called with lifetime held. Reject new callbacks before completing old ones;
// VhfDelete otherwise waits forever for feature transactions in the broker.
void destroy(context *c) {
  VHFHANDLE h;
  {
    guard g(c);
    c->stopping = true;
    h = c->vhf;
    c->vhf = nullptr;
  }
  expire(c, true);
  if (h)
    VhfDelete(h, TRUE);
  {
    guard g(c);
    c->owner = nullptr;
    c->count = c->head = 0;
    c->ready = c->pumping = false;
  }
}
NTSTATUS create(context *c, WDFFILEOBJECT owner) {
  {
    guard g(c);
    if (c->owner)
      return STATUS_DEVICE_BUSY;
  }
  if (!c->opened) {
    WDF_IO_TARGET_OPEN_PARAMS p;
    WDF_IO_TARGET_OPEN_PARAMS_INIT_OPEN_BY_FILE(&p, nullptr);
    auto s = WdfIoTargetOpen(c->target, &p);
    if (!NT_SUCCESS(s))
      return s;
    c->opened = true;
  }
  {
    guard g(c);
    c->owner = owner;
    c->stopping = false;
  }
  static wchar_t ids[] =
      L"HID\\VID_28DE&PID_1304&MI_02\0HID\\VID_28DE&PID_1304\0";
  static wchar_t instance[] = L"MoonmachineSteamExperimental0";
  VHF_CONFIG config;
  VHF_CONFIG_INIT(&config, WdfIoTargetWdmGetTargetFileHandle(c->target),
                  sizeof(descriptor), const_cast<PUCHAR>(descriptor));
  config.VhfClientContext = c;
  config.VendorID = 0x28de;
  config.ProductID = 0x1304;
  config.VersionNumber = 0x100;
  config.HardwareIDs = ids;
  config.HardwareIDsLength = sizeof(ids);
  config.InstanceID = instance;
  config.InstanceIDLength = sizeof(instance);
  config.EvtVhfAsyncOperationGetFeature = get_feature;
  config.EvtVhfAsyncOperationSetFeature = set_feature;
  config.EvtVhfAsyncOperationWriteReport = write_report;
  config.EvtVhfReadyForNextReadReport = ready;
  VHFHANDLE h{};
  auto status = VhfCreate(&config, &h);
  if (NT_SUCCESS(status)) {
    {
      guard g(c);
      c->vhf = h;
    }
    status = VhfStart(h);
  }
  if (!NT_SUCCESS(status))
    destroy(c);
  return status;
}
void ioctl(WDFQUEUE q, WDFREQUEST r, size_t out_size, size_t in_size,
           ULONG code) {
  auto *c = ctx(WdfIoQueueGetDevice(q));
  auto owner = WdfRequestGetFileObject(r);
  NTSTATUS status = STATUS_INVALID_DEVICE_REQUEST;
  size_t bytes = 0;
  WdfWaitLockAcquire(c->lifetime, nullptr);
  bool owned;
  {
    guard g(c);
    owned = c->owner == owner;
  }
  if (code == start && in_size == 0 && out_size == 0)
    status = create(c, owner);
  else if (!owned)
    status = STATUS_ACCESS_DENIED;
  else if (code == stop && in_size == 0 && out_size == 0) {
    destroy(c);
    status = STATUS_SUCCESS;
  } else if (code == input && in_size == sizeof(packet) && out_size == 0) {
    packet *p{};
    status = WdfRequestRetrieveInputBuffer(
        r, sizeof(*p), reinterpret_cast<PVOID *>(&p), nullptr);
    if (NT_SUCCESS(status)) {
      if (!p->size || p->size > 64 || input_size(p->data[0]) != p->size)
        status = STATUS_INVALID_PARAMETER;
      else {
        {
          guard g(c);
          if (c->count == 256)
            status = STATUS_DEVICE_BUSY;
          else {
            c->inputs[(c->head + c->count) % 256] = *p;
            c->count++;
          }
        }
        if (NT_SUCCESS(status))
          pump(c);
      }
    }
  } else if (code == poll && in_size == 0 && out_size == sizeof(packet)) {
    packet *p{};
    status = WdfRequestRetrieveOutputBuffer(
        r, sizeof(*p), reinterpret_cast<PVOID *>(&p), nullptr);
    if (NT_SUCCESS(status)) {
      guard g(c);
      pending *first = nullptr;
      for (auto &pending : c->requests)
        if (pending.handle && !pending.delivered &&
            (!first || pending.request.id < first->request.id))
          first = &pending;
      if (first) {
        *p = first->request;
        first->delivered = true;
        bytes = sizeof(*p);
      } else
        status = STATUS_NO_MORE_ENTRIES;
    }
  } else if (code == reply && in_size == sizeof(response) && out_size == 0) {
    response *p{};
    status = WdfRequestRetrieveInputBuffer(
        r, sizeof(*p), reinterpret_cast<PVOID *>(&p), nullptr);
    if (NT_SUCCESS(status)) {
      VHFOPERATIONHANDLE h{};
      NTSTATUS completion = STATUS_UNSUCCESSFUL;
      status = STATUS_NOT_FOUND;
      {
        guard g(c);
        for (auto &item : c->requests)
          if (item.handle && item.delivered && item.request.id == p->id) {
            completion =
                item.request.op == operation::blocked_feature
                    ? STATUS_NOT_SUPPORTED
                    : (p->status == 0 ? STATUS_SUCCESS : STATUS_UNSUCCESSFUL);
            if (p->status == 0 && item.request.op == operation::get_feature) {
              if (p->size != item.request.size ||
                  p->data[0] != item.request.data[0])
                completion = STATUS_INVALID_PARAMETER;
              else
                std::memcpy(item.transfer->reportBuffer, p->data, p->size);
            }
            h = item.handle;
            item = {};
            status = STATUS_SUCCESS;
            break;
          }
      }
      if (h)
        VhfAsyncOperationComplete(h, completion);
    }
  }
  WdfWaitLockRelease(c->lifetime);
  WdfRequestCompleteWithInformation(r, status, bytes);
}
void file_create(WDFDEVICE, WDFREQUEST r, WDFFILEOBJECT) {
  WdfRequestComplete(r, STATUS_SUCCESS);
}
void file_cleanup(WDFFILEOBJECT f) {
  auto *c = ctx(WdfFileObjectGetDevice(f));
  WdfWaitLockAcquire(c->lifetime, nullptr);
  bool owned;
  {
    guard g(c);
    owned = c->owner == f;
  }
  if (owned)
    destroy(c);
  WdfWaitLockRelease(c->lifetime);
}
NTSTATUS release(WDFDEVICE d, WDFCMRESLIST) {
  auto *c = ctx(d);
  WdfTimerStop(c->timer, TRUE);
  WdfWaitLockAcquire(c->lifetime, nullptr);
  destroy(c);
  if (c->opened) {
    WdfIoTargetClose(c->target);
    c->opened = false;
  }
  WdfWaitLockRelease(c->lifetime);
  return STATUS_SUCCESS;
}
NTSTATUS prepare(WDFDEVICE d, WDFCMRESLIST, WDFCMRESLIST) {
  WdfTimerStart(ctx(d)->timer, WDF_REL_TIMEOUT_IN_MS(100));
  return STATUS_SUCCESS;
}
NTSTATUS add(WDFDRIVER, PWDFDEVICE_INIT init) {
  WdfFdoInitSetFilter(init);
  WDF_FILEOBJECT_CONFIG f;
  WDF_FILEOBJECT_CONFIG_INIT(&f, file_create, nullptr, file_cleanup);
  WdfDeviceInitSetFileObjectConfig(init, &f, WDF_NO_OBJECT_ATTRIBUTES);
  WDF_PNPPOWER_EVENT_CALLBACKS p;
  WDF_PNPPOWER_EVENT_CALLBACKS_INIT(&p);
  p.EvtDevicePrepareHardware = prepare;
  p.EvtDeviceReleaseHardware = release;
  WdfDeviceInitSetPnpPowerEventCallbacks(init, &p);
  WDF_OBJECT_ATTRIBUTES a;
  WDF_OBJECT_ATTRIBUTES_INIT_CONTEXT_TYPE(&a, context);
  WDFDEVICE d{};
  auto s = WdfDeviceCreate(&init, &a, &d);
  if (!NT_SUCCESS(s))
    return s;
  auto *c = ctx(d);
  std::memset(c, 0, sizeof(*c));
  c->stopping = true;
  InitializeSRWLock(&c->lock);
  WDF_OBJECT_ATTRIBUTES_INIT(&a);
  a.ParentObject = d;
  s = WdfWaitLockCreate(&a, &c->lifetime);
  if (!NT_SUCCESS(s))
    return s;
  s = WdfIoTargetCreate(d, &a, &c->target);
  if (!NT_SUCCESS(s))
    return s;
  WDF_TIMER_CONFIG timer;
  WDF_TIMER_CONFIG_INIT_PERIODIC(&timer, tick, 100);
  timer.AutomaticSerialization = FALSE;
  s = WdfTimerCreate(&timer, &a, &c->timer);
  if (!NT_SUCCESS(s))
    return s;
  s = WdfDeviceCreateDeviceInterface(d, &interface_id, nullptr);
  if (!NT_SUCCESS(s))
    return s;
  WDF_IO_QUEUE_CONFIG q;
  WDF_IO_QUEUE_CONFIG_INIT_DEFAULT_QUEUE(&q, WdfIoQueueDispatchSequential);
  q.PowerManaged = WdfTrue;
  q.EvtIoDeviceControl = ioctl;
  return WdfIoQueueCreate(d, &q, WDF_NO_OBJECT_ATTRIBUTES, nullptr);
}
extern "C" NTSTATUS DriverEntry(PDRIVER_OBJECT d, PUNICODE_STRING p) {
  WDF_DRIVER_CONFIG c;
  WDF_DRIVER_CONFIG_INIT(&c, add);
  return WdfDriverCreate(d, p, WDF_NO_OBJECT_ATTRIBUTES, &c, WDF_NO_HANDLE);
}
