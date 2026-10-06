// Keep Verovio's scoped CSS and glyph references valid when combining SVGs.
export function namespaceSvg(svg, prefix) {
  const ids = new Set([...svg.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]));
  return svg.replace(/\bid="([^"]+)"/g, (_, id) => `id="${prefix}${id}"`)
    .replace(/href="#([^"]+)"/g, (_, id) => `href="#${prefix}${id}"`)
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/g, css =>
      css.replace(/#([\w-]+)/g, (whole, id) => ids.has(id) ? `#${prefix}${id}` : whole));
}

// Offline soft piano-like synthesis; no remote samples or licensing dependency.
export function softTone(ctx, destination, midi, time, duration, nodes) {
  const filter = ctx.createBiquadFilter();
  filter.type = 'lowpass'; filter.frequency.value = 2600; filter.Q.value = 0.3;
  filter.connect(destination);
  const end = time + duration + 0.12;
  [1, 2, 3].forEach((partial, i) => {
    const oscillator = ctx.createOscillator(), gain = ctx.createGain();
    oscillator.type = 'sine';
    oscillator.frequency.value = 440 * 2 ** ((midi - 69) / 12) * partial;
    const peak = [0.15, 0.025, 0.008][i];
    const attack = Math.min(0.018, duration / 4);
    gain.gain.setValueAtTime(0, time);
    gain.gain.linearRampToValueAtTime(peak, time + attack);
    gain.gain.exponentialRampToValueAtTime(Math.max(0.0001, peak * 0.15), time + duration);
    gain.gain.linearRampToValueAtTime(0, end);
    oscillator.connect(gain); gain.connect(filter);
    oscillator.start(time); oscillator.stop(end);
    oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); if (i === 2) filter.disconnect(); };
    nodes.push(oscillator);
  });
}
