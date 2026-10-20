// Minimal WebAudio SFX. Platform edge: no gameplay meaning lives here.

let ctx = null;

function audio() {
  if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
  return ctx;
}

export function unlockAudio() {
  try {
    const a = audio();
    if (a.state === 'suspended') a.resume();
  } catch (error) {
    /* audio is optional */
  }
}

export function sfx(type) {
  try {
    const ac = audio();
    const osc = ac.createOscillator();
    const gain = ac.createGain();
    osc.connect(gain);
    gain.connect(ac.destination);
    const t = ac.currentTime;

    if (type === 'fire') {
      osc.type = 'square';
      osc.frequency.setValueAtTime(240, t);
      osc.frequency.exponentialRampToValueAtTime(70, t + 0.12);
      gain.gain.setValueAtTime(0.06, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.12);
      osc.start(t);
      osc.stop(t + 0.13);
    } else if (type === 'boom') {
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(130, t);
      osc.frequency.exponentialRampToValueAtTime(28, t + 0.4);
      gain.gain.setValueAtTime(0.15, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.45);
      osc.start(t);
      osc.stop(t + 0.5);
    } else if (type === 'pick') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(660, t);
      osc.frequency.setValueAtTime(990, t + 0.08);
      gain.gain.setValueAtTime(0.1, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.25);
      osc.start(t);
      osc.stop(t + 0.3);
    } else {
      osc.disconnect();
      gain.disconnect();
    }
  } catch (error) {
    /* audio is optional */
  }
}
