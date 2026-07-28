/**
 * Microphone capture, on the audio thread.
 *
 * The worklet is handed 128-sample blocks. Sending one WebSocket frame per
 * block would be ~125 frames a second, so blocks are batched into ~100 ms
 * chunks first. Float32 is converted to PCM16 here rather than on the server:
 * it halves what goes over the wire and it is the format the recogniser wants.
 */
const CHUNK = 1600; // 100 ms at 16 kHz

class CaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = new Float32Array(CHUNK);
    this.filled = 0;
  }

  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!channel) return true; // no input yet; keep the node alive

    for (let i = 0; i < channel.length; i++) {
      this.buffer[this.filled++] = channel[i];
      if (this.filled === CHUNK) {
        const pcm = new Int16Array(CHUNK);
        for (let s = 0; s < CHUNK; s++) {
          const clamped = Math.max(-1, Math.min(1, this.buffer[s]));
          pcm[s] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
        }
        this.port.postMessage(pcm.buffer, [pcm.buffer]);
        this.filled = 0;
      }
    }
    return true;
  }
}

registerProcessor("capture", CaptureProcessor);
