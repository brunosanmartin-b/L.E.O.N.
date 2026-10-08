/* ====================================
   L.E.O.N. - Lógica de la interfaz
   Recibe eventos en vivo desde main.py (Server-Sent Events)
   ==================================== */
(() => {
    'use strict';

    const $ = (id) => document.getElementById(id);
    const el = {
        conn: $('conn'), connText: $('conn-text'), clock: $('clock'),
        wake: $('info-wake'), voice: $('info-voice'), model: $('info-model'),
        uptime: $('uptime'), count: $('count'), skills: $('skills'), log: $('log'),
        label: $('status-label'), detail: $('status-detail'),
        chat: $('chat'), chatEmpty: $('chat-empty'),
        form: $('composer'), input: $('composer-input'), send: $('composer-send'),
        orb: $('orb'),
    };

    const STATES = {
        idle:      { label: 'EN ESPERA',   color: [255, 59, 59],  spin: 0.15, breathe: 1 },
        listening: { label: 'ESCUCHANDO',  color: [255, 77, 77],  spin: 0.35, breathe: 1.4 },
        thinking:  { label: 'PROCESANDO',  color: [255, 178, 89], spin: 1.6,  breathe: 0.6 },
        speaking:  { label: 'HABLANDO',    color: [255, 107, 91], spin: 0.4,  breathe: 1 },
        offline:   { label: 'DESCONECTADO', color: [108, 95, 104], spin: 0.05, breathe: 0.4 },
    };

    // Frases de ejemplo para los botones de habilidades (deben contener la palabra clave)
    const SKILL_PHRASES = { hora: '¿Qué hora es?', spotify: 'Abre Spotify' };

    let state = 'offline';
    let startedAt = null;
    let interactions = 0;
    let connected = false;

    // ---------- Utilidades ----------
    const pad = (n) => String(n).padStart(2, '0');
    const fmtTime = (ts) => {
        const d = ts ? new Date(ts * 1000) : new Date();
        return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    };
    const prettyVoice = (v) => (v || '—').replace(/Neural$/, '').replace(/^([a-z]{2})-([A-Z]{2})-/, '$1-$2 · ');

    // ---------- Reloj y uptime ----------
    function tick() {
        el.clock.textContent = fmtTime();
        if (startedAt && connected) {
            const s = Math.max(0, Math.floor(Date.now() / 1000 - startedAt));
            el.uptime.textContent = `${pad(Math.floor(s / 3600))}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}`;
        }
    }
    setInterval(tick, 1000);
    tick();

    // ---------- Estado ----------
    function setState(next, detail) {
        state = STATES[next] ? next : 'idle';
        document.body.className = `state-${state}`;
        el.label.textContent = STATES[state].label;
        if (detail !== undefined) el.detail.textContent = detail;
    }

    function setConnected(on) {
        connected = on;
        el.conn.classList.toggle('online', on);
        el.connText.textContent = on ? 'Núcleo en línea' : 'Sin conexión';
        el.input.disabled = el.send.disabled = !on;
        el.skills.querySelectorAll('button').forEach((b) => (b.disabled = !on));
        if (!on) {
            setState('offline');
            el.detail.innerHTML = location.protocol === 'file:'
                ? 'Abre la interfaz desde <code>http://127.0.0.1:8765</code>'
                : 'Inicia el núcleo con <code>python main.py</code>';
        }
    }

    // ---------- Registro y chat ----------
    function addLog({ level = 'system', msg, ts }) {
        const li = document.createElement('li');
        li.className = level;
        const time = document.createElement('time');
        time.textContent = fmtTime(ts);
        const span = document.createElement('span');
        span.textContent = msg;
        li.append(time, span);
        el.log.append(li);
        while (el.log.children.length > 80) el.log.firstChild.remove();
        el.log.scrollTop = el.log.scrollHeight;
    }

    function addMessage({ role, text, ts }) {
        el.chatEmpty.hidden = true;
        const div = document.createElement('div');
        div.className = `msg msg-${role}`;
        div.textContent = text;
        const time = document.createElement('time');
        time.textContent = fmtTime(ts);
        div.append(time);
        el.chat.append(div);
        el.chat.scrollTop = el.chat.scrollHeight;
        if (role === 'user') el.count.textContent = ++interactions;
    }

    function renderSkills(skills) {
        el.skills.replaceChildren();
        if (!skills || !skills.length) {
            el.skills.innerHTML = '<span class="muted">Sin habilidades</span>';
            return;
        }
        for (const key of skills) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'skill';
            btn.textContent = SKILL_PHRASES[key] || key.charAt(0).toUpperCase() + key.slice(1);
            btn.disabled = !connected;
            btn.addEventListener('click', () => sendCommand(SKILL_PHRASES[key] || key));
            el.skills.append(btn);
        }
    }

    // ---------- Envío de comandos escritos ----------
    async function sendCommand(text) {
        text = text.trim();
        if (!text || !connected) return;
        try {
            const res = await fetch('/api/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            });
            if (!res.ok) throw new Error(res.status);
        } catch {
            addLog({ level: 'error', msg: 'No se pudo enviar el comando' });
        }
    }

    el.form.addEventListener('submit', (e) => {
        e.preventDefault();
        sendCommand(el.input.value);
        el.input.value = '';
    });

    // ---------- Conexión en vivo ----------
    let level = 0;          // nivel de audio objetivo (mic o voz)
    let levelSmooth = 0;

    function handleEvent(ev) {
        switch (ev.type) {
            case 'hello': {
                const info = ev.info || {};
                el.wake.textContent = info.wakeWord ? `“${info.wakeWord}”` : '—';
                el.voice.textContent = prettyVoice(info.voice);
                el.voice.title = info.voice || '';
                el.model.textContent = info.model || '—';
                startedAt = ev.startedAt;
                renderSkills(info.skills);
                el.log.replaceChildren();
                el.chat.querySelectorAll('.msg').forEach((m) => m.remove());
                interactions = 0;
                el.count.textContent = '0';
                el.chatEmpty.hidden = false;
                (ev.recent || []).forEach(handleEvent);
                setState(ev.state, ev.detail || '');
                break;
            }
            case 'state': setState(ev.state, ev.detail || ''); break;
            case 'log': addLog(ev); break;
            case 'message': addMessage(ev); break;
            case 'level': level = ev.value; break;
        }
    }

    if (location.protocol === 'file:') {
        setConnected(false);
    } else {
        const source = new EventSource('/events');
        source.onopen = () => setConnected(true);
        source.onerror = () => setConnected(false);  // EventSource reintenta solo
        source.onmessage = (m) => {
            try { handleEvent(JSON.parse(m.data)); } catch (err) { console.error(err); }
        };
    }
    setConnected(false);

    // ---------- Orbe animado ----------
    const ctx = el.orb.getContext('2d');
    const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
    let color = [...STATES.offline.color];
    let spin = 0, angle = 0;

    function resize() {
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        const { width, height } = el.orb.getBoundingClientRect();
        el.orb.width = Math.round(width * dpr);
        el.orb.height = Math.round(height * dpr);
    }
    new ResizeObserver(resize).observe(el.orb);
    resize();

    const rgba = (c, a) => `rgba(${c[0] | 0}, ${c[1] | 0}, ${c[2] | 0}, ${a})`;

    function draw(now) {
        const t = now / 1000;
        const cfg = STATES[state];
        const W = el.orb.width, H = el.orb.height;
        const cx = W / 2, cy = H / 2, R = Math.min(W, H) / 2;

        // Interpolaciones suaves hacia el estado actual
        color = color.map((v, i) => v + (cfg.color[i] - v) * 0.06);
        spin += (cfg.spin - spin) * 0.05;
        angle += spin * 0.016 * (reduceMotion ? 0.2 : 1);
        level *= 0.92;  // si dejan de llegar eventos, el nivel decae
        levelSmooth += (level - levelSmooth) * 0.25;

        const breathe = reduceMotion ? 0 : Math.sin(t * 1.6 * cfg.breathe) * 0.5 + 0.5;
        const energy = levelSmooth;

        ctx.clearRect(0, 0, W, H);

        // Halo exterior
        const halo = ctx.createRadialGradient(cx, cy, R * 0.15, cx, cy, R);
        halo.addColorStop(0, rgba(color, 0.22 + energy * 0.25));
        halo.addColorStop(0.55, rgba(color, 0.05 + energy * 0.06));
        halo.addColorStop(1, rgba(color, 0));
        ctx.fillStyle = halo;
        ctx.fillRect(0, 0, W, H);

        // Anillo de marcas
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(angle * 0.3);
        const ticks = 96;
        for (let i = 0; i < ticks; i++) {
            const a = (i / ticks) * Math.PI * 2;
            const major = i % 8 === 0;
            const r1 = R * 0.86, r2 = R * (major ? 0.81 : 0.835);
            ctx.strokeStyle = rgba(color, major ? 0.55 : 0.18);
            ctx.lineWidth = major ? 2 : 1;
            ctx.beginPath();
            ctx.moveTo(Math.cos(a) * r1, Math.sin(a) * r1);
            ctx.lineTo(Math.cos(a) * r2, Math.sin(a) * r2);
            ctx.stroke();
        }
        ctx.restore();

        // Arcos orbitales
        const arcs = [
            { r: 0.74, len: 1.3, speed: 1, w: 2, a: 0.7 },
            { r: 0.67, len: 0.7, speed: -1.6, w: 1.5, a: 0.45 },
            { r: 0.62, len: 2.2, speed: 0.6, w: 1, a: 0.3 },
        ];
        ctx.lineCap = 'round';
        for (const arc of arcs) {
            const start = angle * arc.speed * 2;
            ctx.strokeStyle = rgba(color, arc.a);
            ctx.lineWidth = arc.w * (W / 440);
            ctx.beginPath();
            ctx.arc(cx, cy, R * arc.r, start, start + arc.len);
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(cx, cy, R * arc.r, start + Math.PI, start + Math.PI + arc.len * 0.4);
            ctx.stroke();
        }

        // Núcleo deformable (reacciona a la voz / micrófono)
        const base = R * (0.36 + breathe * 0.015 + energy * 0.08);
        const points = 120;
        ctx.beginPath();
        for (let i = 0; i <= points; i++) {
            const a = (i / points) * Math.PI * 2;
            const wobble =
                Math.sin(a * 3 + t * 1.7) * 0.5 +
                Math.sin(a * 5 - t * 2.3) * 0.3 +
                Math.sin(a * 7 + t * 3.1) * 0.2;
            const r = base * (1 + wobble * (0.015 + energy * 0.18));
            const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
            i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
        }
        ctx.closePath();
        const core = ctx.createRadialGradient(cx - base * 0.3, cy - base * 0.35, base * 0.05, cx, cy, base * 1.05);
        core.addColorStop(0, 'rgba(255, 236, 228, 0.95)');
        core.addColorStop(0.25, rgba(color, 0.95));
        core.addColorStop(0.8, rgba(color.map((v) => v * 0.45), 0.95));
        core.addColorStop(1, rgba(color.map((v) => v * 0.25), 0.9));
        ctx.shadowColor = rgba(color, 0.8);
        ctx.shadowBlur = R * (0.12 + energy * 0.15);
        ctx.fillStyle = core;
        ctx.fill();
        ctx.shadowBlur = 0;

        // Contorno fino
        ctx.strokeStyle = rgba([255, 220, 210], 0.25);
        ctx.lineWidth = 1;
        ctx.stroke();

        requestAnimationFrame(draw);
    }
    requestAnimationFrame(draw);
})();
