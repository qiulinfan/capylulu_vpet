window.__ModuleLoader__.load({
	id: "capylulu-pet",
	factory: (require) => {
		var module = { exports: {} };
		var exports = module.exports;
		Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
		let react = require("react");

		const inject = ["slots"];

		// Placeholders replaced by scripts/build-client.mjs (atlas data URL + manifest).
		const ATLAS_SRC = "__ATLAS_DATA_URL__";
		const MANIFEST = __MANIFEST_JSON__;

		const CSS_ID = "capylulu-pet/styles";
		const CSS_TEXT =
			".clp-root{position:absolute;right:18px;bottom:10px;z-index:30;pointer-events:none;display:flex;flex-direction:column;align-items:center;user-select:none}" +
			".clp-canvas{pointer-events:auto;cursor:pointer;width:96px;height:104px;image-rendering:pixelated;filter:drop-shadow(0 6px 10px rgba(0,0,0,.35))}" +
			".clp-shadow{width:54px;height:10px;margin-top:-8px;border-radius:50%;background:radial-gradient(ellipse at center,rgba(0,0,0,.30) 0%,rgba(0,0,0,0) 70%)}" +
			".clp-bubble{pointer-events:none;position:relative;margin-bottom:6px;padding:5px 11px;border-radius:12px;font-size:12px;line-height:1.5;white-space:nowrap;color:inherit;background:var(--dsw-alias-bg-raised,#ffffff);border:1px solid var(--dsw-alias-border-l2,rgba(0,0,0,.14));box-shadow:0 4px 14px rgba(0,0,0,.20);animation:clp-pop .18s ease-out}" +
			"@keyframes clp-pop{from{transform:translateY(4px) scale(.92);opacity:0}to{transform:none;opacity:1}}";

		function ensureStyles() {
			if (typeof document === "undefined") return;
			if (document.querySelector("style[data-plugin-css=\"" + CSS_ID + "\"]")) return;
			const tag = document.createElement("style");
			tag.dataset.plugin = "capylulu-pet";
			tag.dataset.pluginCss = CSS_ID;
			tag.textContent = CSS_TEXT;
			document.head.appendChild(tag);
		}

		const GREETINGS = ["噜噜！", "你好呀～", "加油鸭！", "今天也要元气满满！"];
		const DONE_LINES = ["搞定啦！", "成功收工！", "棒棒哒！", "任务完成，噜噜！"];
		const FAIL_LINES = ["哎呀，出错了…", "别急，我再看一眼"];

		const STATE_LABELS = {
			idle: "睡觉中…",
			waiting: "等你吩咐～",
			running: "干活中！",
			wave: "嗨！",
			failed: "出错了…"
		};

		const REDUCED_MOTION = typeof matchMedia !== "undefined"
			? matchMedia("(prefers-reduced-motion: reduce)").matches
			: false;

		function pick(lines) {
			return lines[Math.floor(Math.random() * lines.length)];
		}

		function CapyLuluPet(props) {
			const useSessions = props.useSessions;
			const current = useSessions(function (s) { return s.current ?? null; });
			const running = useSessions(function (s) {
				return s.current ? (s.byId[s.current]?.running ?? false) : false;
			});
			const completed = useSessions(function (s) {
				return s.current ? (s.byId[s.current]?.completed ?? false) : false;
			});
			const failedJob = useSessions(function (s) {
				if (!s.current) return false;
				const jobs = s.jobsBySession[s.current];
				return jobs ? jobs.some(function (j) { return j.status === "failed"; }) : false;
			});

			const [override, setOverride] = react.useState(null);
			const [frame, setFrame] = react.useState(0);
			const [img, setImg] = react.useState(null);
			const canvasRef = react.useRef(null);

			react.useEffect(function () {
				let alive = true;
				const image = new Image();
				image.onload = function () { if (alive) setImg(image); };
				image.src = ATLAS_SRC;
				return function () { alive = false; };
			}, []);

			function celebrate(lines, duration, mood) {
				setOverride({
					mood: mood || "wave",
					until: Date.now() + duration,
					bubble: pick(lines)
				});
			}

			const prevRunning = react.useRef(running);
			react.useEffect(function () {
				if (prevRunning.current === running) return;
				const was = prevRunning.current;
				prevRunning.current = running;
				if (!was && running) {
					setOverride(null);
				} else if (was && !running) {
					celebrate(DONE_LINES, 3600, "wave");
				}
			}, [running]);

			const prevCompleted = react.useRef(completed);
			react.useEffect(function () {
				if (prevCompleted.current === completed) return;
				prevCompleted.current = completed;
				if (completed) celebrate(DONE_LINES, 3600, "wave");
			}, [completed]);

			const prevFailed = react.useRef(failedJob);
			react.useEffect(function () {
				if (prevFailed.current === failedJob) return;
				prevFailed.current = failedJob;
				if (failedJob) celebrate(FAIL_LINES, 4200, "failed");
			}, [failedJob]);

			react.useEffect(function () {
				if (!override) return;
				const remaining = override.until - Date.now();
				if (remaining <= 0) { setOverride(null); return; }
				const timer = setTimeout(function () { setOverride(null); }, remaining);
				return function () { clearTimeout(timer); };
			}, [override]);

			const mood = (function () {
				if (override && override.until > Date.now()) return override.mood;
				if (running) return "running";
				if (current) return "waiting";
				return "idle";
			})();

			react.useEffect(function () {
				setFrame(0);
				if (REDUCED_MOTION) return;
				const state = MANIFEST.states[mood];
				let index = 0;
				let timer = null;
				const tick = function () {
					index = (index + 1) % state.count;
					setFrame(index);
					timer = setTimeout(tick, state.durations[index % state.durations.length]);
				};
				timer = setTimeout(tick, state.durations[0]);
				return function () { if (timer !== null) clearTimeout(timer); };
			}, [mood]);

			react.useEffect(function () {
				const canvas = canvasRef.current;
				if (!canvas || !img) return;
				const state = MANIFEST.states[mood];
				const cellW = MANIFEST.cellSize[0];
				const cellH = MANIFEST.cellSize[1];
				const dpr = window.devicePixelRatio || 1;
				canvas.width = Math.round(cellW * dpr);
				canvas.height = Math.round(cellH * dpr);
				const ctx = canvas.getContext("2d");
				ctx.clearRect(0, 0, canvas.width, canvas.height);
				ctx.imageSmoothingEnabled = false;
				ctx.drawImage(
					img,
					(state.column + frame) * cellW,
					state.row * cellH,
					cellW,
					cellH,
					0,
					0,
					canvas.width,
					canvas.height
				);
			}, [frame, mood, img]);

			const onClick = react.useCallback(function () {
				celebrate(GREETINGS, 2600, "wave");
			}, []);

			const bubble = override && override.until > Date.now() ? override.bubble : null;
			const label = STATE_LABELS[mood] || mood;

			return react.createElement(
				"div",
				{ className: "clp-root", title: "水豚噜噜 · " + label + "（点击打招呼）" },
				bubble ? react.createElement("div", { className: "clp-bubble", key: bubble }, bubble) : null,
				react.createElement("canvas", {
					ref: canvasRef,
					className: "clp-canvas",
					onClick: onClick,
					role: "img",
					"aria-label": "水豚噜噜：" + label
				}),
				react.createElement("div", { className: "clp-shadow" })
			);
		}

		function apply(ctx) {
			ctx.effect(function () {
				ensureStyles();
				const dispose = ctx.slots.register(
					{
						name: "shell.overlay",
						id: "capylulu-pet",
						order: 0,
						label: "水豚噜噜桌面宠物",
						priority: 0,
						registrant: "capylulu-pet"
					},
					CapyLuluPet
				);
				return function () { dispose(); };
			}, "capylulu-pet: shell overlay pet");
		}

		exports.apply = apply;
		exports.inject = inject;
		return module.exports;
	}
});
