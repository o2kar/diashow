(function () {
  "use strict";

  const REFETCH_INTERVAL_MS = 5 * 60 * 1000;
  const EMPTY_POLL_INTERVAL_MS = 10 * 1000;
  const PRELOAD_TIMEOUT_MS = 3000;

  const slug = window.SLIDESHOW_SLUG;
  const placeholder = document.getElementById("placeholder");
  const slotEls = [document.getElementById("slotA"), document.getElementById("slotB")];

  function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function createElementFor(item) {
    if (item.type === "image") {
      const img = document.createElement("img");
      img.src = item.url;
      img.alt = "";
      return img;
    }
    const video = document.createElement("video");
    video.src = item.url;
    video.muted = true;
    video.playsInline = true;
    video.controls = false;
    video.preload = "auto";
    return video;
  }

  function waitReady(el, item) {
    return new Promise((resolve) => {
      let done = false;
      const finish = () => {
        if (done) return;
        done = true;
        resolve();
      };
      const timer = setTimeout(finish, PRELOAD_TIMEOUT_MS);
      const onReady = () => {
        clearTimeout(timer);
        finish();
      };
      if (item.type === "image") {
        if (el.complete) {
          clearTimeout(timer);
          finish();
        } else {
          el.addEventListener("load", onReady, { once: true });
          el.addEventListener("error", onReady, { once: true });
        }
      } else {
        el.addEventListener("loadeddata", onReady, { once: true });
        el.addEventListener("error", onReady, { once: true });
      }
    });
  }

  class Player {
    constructor() {
      this.slots = [
        { el: slotEls[0], item: null },
        { el: slotEls[1], item: null },
      ];
      this.currentSlotIdx = 0;
      this.media = [];
      this.imageDurationSeconds = 8;
      this.index = 0;
      this.advanceTimer = null;
      this.nextReadyPromise = Promise.resolve();
      this.pendingData = null;
    }

    async init() {
      await this.fetchAndMaybeStart();
      setInterval(() => this.refetch(), REFETCH_INTERVAL_MS);
      document.addEventListener("keydown", (e) => {
        if (e.key === "f" && document.documentElement.requestFullscreen) {
          document.documentElement.requestFullscreen().catch(() => {});
        }
      });
    }

    async fetchShow() {
      const res = await fetch(`/api/show/${encodeURIComponent(slug)}`, { cache: "no-store" });
      if (!res.ok) throw new Error("failed to load show data");
      return res.json();
    }

    applyData(data) {
      this.media = (data.media || []).slice().sort((a, b) => a.position - b.position);
      this.imageDurationSeconds = data.image_duration_seconds || 8;
    }

    async fetchAndMaybeStart() {
      let data;
      try {
        data = await this.fetchShow();
      } catch (e) {
        setTimeout(() => this.fetchAndMaybeStart(), EMPTY_POLL_INTERVAL_MS);
        return;
      }
      this.applyData(data);
      if (this.media.length === 0) {
        this.showPlaceholder();
        setTimeout(() => this.fetchAndMaybeStart(), EMPTY_POLL_INTERVAL_MS);
      } else {
        this.hidePlaceholder();
        this.index = 0;
        this.start();
      }
    }

    async refetch() {
      try {
        this.pendingData = await this.fetchShow();
      } catch (e) {
        // transient network error; keep showing current content
      }
    }

    showPlaceholder() {
      placeholder.hidden = false;
    }

    hidePlaceholder() {
      placeholder.hidden = true;
    }

    renderIntoSlot(slot, item) {
      slot.el.innerHTML = "";
      const el = createElementFor(item);
      slot.el.appendChild(el);
      slot.item = item;
      return { el, ready: waitReady(el, item) };
    }

    clearAdvanceTimer() {
      if (this.advanceTimer) {
        clearTimeout(this.advanceTimer);
        this.advanceTimer = null;
      }
    }

    scheduleAdvance(mediaEl, item) {
      this.clearAdvanceTimer();
      if (item.type === "image") {
        this.advanceTimer = setTimeout(() => this.advance(), this.imageDurationSeconds * 1000);
      } else {
        mediaEl.currentTime = 0;
        mediaEl.addEventListener("ended", () => this.advance(), { once: true });
        mediaEl.play().catch(() => {
          // autoplay blocked or media error: fall back to the configured
          // image duration so the show doesn't stall on this slide forever
          this.advanceTimer = setTimeout(() => this.advance(), this.imageDurationSeconds * 1000);
        });
      }
    }

    preloadNext() {
      if (this.media.length <= 1) {
        this.nextReadyPromise = Promise.resolve();
        return;
      }
      const nextIdx = (this.index + 1) % this.media.length;
      const nextItem = this.media[nextIdx];
      const inactive = this.slots[1 - this.currentSlotIdx];
      if (inactive.item && inactive.item.id === nextItem.id) {
        this.nextReadyPromise = Promise.resolve();
        return;
      }
      const { ready } = this.renderIntoSlot(inactive, nextItem);
      this.nextReadyPromise = ready;
    }

    start() {
      this.currentSlotIdx = 0;
      const current = this.slots[0];
      const { el, ready } = this.renderIntoSlot(current, this.media[this.index]);
      ready.then(() => {
        current.el.classList.add("current");
        this.scheduleAdvance(el, this.media[this.index]);
        this.preloadNext();
      });
    }

    replayInPlace() {
      const current = this.slots[this.currentSlotIdx];
      const el = current.el.querySelector("img, video");
      if (!el) return;
      this.scheduleAdvance(el, this.media[this.index]);
    }

    async advance() {
      this.clearAdvanceTimer();

      if (this.media.length <= 1) {
        this.replayInPlace();
        return;
      }

      await Promise.race([this.nextReadyPromise, delay(PRELOAD_TIMEOUT_MS)]);

      const oldSlot = this.slots[this.currentSlotIdx];
      const newSlot = this.slots[1 - this.currentSlotIdx];

      oldSlot.el.classList.add("transitioning");
      newSlot.el.classList.add("transitioning");

      requestAnimationFrame(() => {
        oldSlot.el.classList.remove("current");
        oldSlot.el.classList.add("exiting");
        newSlot.el.classList.add("current");
      });

      const cleanup = () => {
        oldSlot.el.classList.remove("transitioning", "exiting");
        newSlot.el.classList.remove("transitioning");
        const oldVideo = oldSlot.el.querySelector("video");
        if (oldVideo) oldVideo.pause();
        // Only safe to overwrite oldSlot's content now that it's parked
        // off-screen again — doing this earlier, while it's still visibly
        // animating out, causes the upcoming item to flash through mid-transition.
        this.preloadNext();
      };
      oldSlot.el.addEventListener("transitionend", cleanup, { once: true });

      this.currentSlotIdx = 1 - this.currentSlotIdx;
      const nextIndex = (this.index + 1) % this.media.length;
      const isLoopBoundary = nextIndex === 0;
      this.index = nextIndex;

      if (isLoopBoundary && this.pendingData) {
        this.applyData(this.pendingData);
        this.pendingData = null;
        this.index = 0;
        if (this.media.length === 0) {
          this.showPlaceholder();
          this.clearAdvanceTimer();
          setTimeout(() => this.fetchAndMaybeStart(), EMPTY_POLL_INTERVAL_MS);
          return;
        }
      }

      const newItem = this.media[this.index];
      const newEl = newSlot.el.querySelector("img, video") || newSlot.el.firstElementChild;

      if (!newSlot.item || newSlot.item.id !== newItem.id) {
        // pending-data swap changed what belongs in this slot; load it fresh
        const { el, ready } = this.renderIntoSlot(newSlot, newItem);
        ready.then(() => this.scheduleAdvance(el, newItem));
      } else {
        this.scheduleAdvance(newEl, newItem);
      }
    }
  }

  new Player().init();
})();
