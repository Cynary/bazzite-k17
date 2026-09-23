/* Exercise the same SDL2 rumble APIs used by Moonlight. No network required. */
#include <SDL.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static volatile sig_atomic_t stopped;
static void stop(int sig) { (void)sig; stopped = 1; }
static int wait_ms(SDL_GameController *pad, unsigned ms) {
    Uint32 end = SDL_GetTicks() + ms;
    while (!stopped && (Sint32)(end-SDL_GetTicks()) > 0) {
        SDL_PumpEvents();
        if (!SDL_GameControllerGetAttached(pad)) return -1;
        SDL_Delay(10);
    }
    return stopped ? -1 : 0;
}
int main(int argc, char **argv) {
    int rc=1;
    SDL_GameController *pad=NULL;
    signal(SIGINT, stop); signal(SIGTERM, stop);
    SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");
    if (SDL_Init(SDL_INIT_GAMECONTROLLER|SDL_INIT_HAPTIC) < 0) goto error;
    for (int i=0;i<SDL_NumJoysticks();i++) {
        printf("%d: %s [%04x:%04x] %s\n",i,SDL_JoystickNameForIndex(i),
            SDL_JoystickGetDeviceVendor(i),SDL_JoystickGetDeviceProduct(i),
            SDL_IsGameController(i)?"gamepad":"unmapped");
    }
    if (argc==2 && !strcmp(argv[1],"--list")) { rc=0; goto done; }
    if (argc!=3 || strcmp(argv[1],"--run")) {
        fprintf(stderr,"Usage: %s --list | --run INDEX\n",argv[0]);goto done;
    }
    char *end; long index=strtol(argv[2],&end,10);
    if (!*argv[2] || *end || index<0 || index>=SDL_NumJoysticks()) goto error;
    pad=SDL_GameControllerOpen((int)index);
    if (!pad) goto error;
    if (!SDL_GameControllerHasRumble(pad) || !SDL_GameControllerHasRumbleTriggers(pad)) {
        fprintf(stderr,"Selected device does not expose both grip and trigger rumble.\n"
            "Check candidate kernel, xone, SDL and whether Steam substituted a virtual pad.\n");
        goto done;
    }
    printf("Four-motor capability confirmed. Hold the controller with fingers resting on the triggers.\n"
           "Press Enter to run; Ctrl+C stops. Each pulse lasts one second at 35%% strength.\n");
    fflush(stdout); if (getchar()==EOF || stopped) goto done;
    const struct { const char *name; Uint16 l,r,lt,rt; } steps[]={
        {"LEFT GRIP only",22937,0,0,0}, {"RIGHT GRIP only",0,22937,0,0},
        {"LEFT TRIGGER only",0,0,22937,0}, {"RIGHT TRIGGER only",0,0,0,22937},
        {"LEFT GRIP + RIGHT TRIGGER",22937,0,0,22937},
        {"RIGHT TRIGGER continues; grip stops",0,0,0,22937},
        {"LEFT GRIP + RIGHT TRIGGER",22937,0,0,22937},
        {"LEFT GRIP continues; trigger stops",22937,0,0,0},
    };
    for (unsigned i=0;i<sizeof(steps)/sizeof(steps[0]);i++) {
        printf("%u: %s\n",i+1,steps[i].name);fflush(stdout);
        if (SDL_GameControllerRumble(pad,steps[i].l,steps[i].r,1500)<0 ||
            SDL_GameControllerRumbleTriggers(pad,steps[i].lt,steps[i].rt,1500)<0) goto error;
        if (wait_ms(pad,1000)<0) goto done;
        if (i<3) {
            SDL_GameControllerRumble(pad,0,0,0);SDL_GameControllerRumbleTriggers(pad,0,0,0);
            if (wait_ms(pad,500)<0) goto done;
        }
    }
    puts("Sequence finished. Confirm what you felt; successful API calls alone do not prove motor output.");
    rc=0;goto done;
error:
    fprintf(stderr,"SDL: %s\n",SDL_GetError());
done:
    if (pad) {
        SDL_GameControllerRumble(pad,0,0,0);
        SDL_GameControllerRumbleTriggers(pad,0,0,0);
        SDL_GameControllerClose(pad);
    }
    SDL_Quit();return rc;
}
