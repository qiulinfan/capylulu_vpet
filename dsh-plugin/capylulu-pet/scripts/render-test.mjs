// SSR-render CapyLuluPet with a mock useSessions to catch component runtime errors.
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const bundlePath = "C:/Users/rynne/Desktop/capylulu_vpet/dsh-plugin/capylulu-pet/lib/client.js";
const profileModules = "C:/Users/rynne/.dsh/profiles/web/node_modules";
const requireFromProfile = createRequire(profileModules + "/x.js");

const source = readFileSync(bundlePath, "utf8");
const registrations = [];
const sandbox = {
  window: { __ModuleLoader__: { load: (e) => registrations.push(e) } },
  matchMedia: undefined, Image: undefined, document: undefined,
  setTimeout, clearTimeout, Date, Math, Symbol, Object, Array, JSON, console,
};
vm.createContext(sandbox);
vm.runInContext(source, sandbox, { filename: "client.js" });
const result = registrations[0].factory(requireFromProfile);

const React = requireFromProfile("react");
const { renderToString } = requireFromProfile("react-dom/server");

// mock snapshot store: subscribe/getSnapshot per selector
const state = {
  ids: ["s1"],
  byId: { s1: { id: "s1", running: true, completed: false, blank: false } },
  current: "s1",
  phase: "ready",
  subagentsByParent: {},
  jobsBySession: { s1: [{ id: "pwsh-1", kind: "pwsh", label: "x", status: "running" }] },
  currentAddress: undefined,
};
const listeners = new Set();
function emit(next) {
  Object.assign(state, next);
  for (const fn of [...listeners]) fn();
}
function useSessionsMock(selector) {
  const [value, setValue] = React.useState(() => selector(state));
  React.useEffect(() => {
    listeners.add(onChange);
    return () => listeners.delete(onChange);
    function onChange() {
      setValue(selector(state));
    }
  }, []);
  return value;
}

// extract component: the registered component was captured with the fake slots;
// instead grab it from the module exports... we only export apply/inject.
// Re-run apply with a capture to get the component.
let captured = null;
const fakeSlots = {
  register(options, component) {
    captured = component;
    return () => {};
  },
};
result.apply({
  slots: fakeSlots,
  effect(fn) {
    const dispose = fn();
    if (typeof dispose === "function") dispose();
  },
});
const Comp = captured;
const html = renderToString(React.createElement(Comp, { useSessions: useSessionsMock, useWorkspaces: () => ({ phase: "ready", ids: [], byId: {} }) }));
console.log("rendered html length:", html.length);
console.log(html.slice(0, 400));
if (!html.includes("clp-root")) throw new Error("clp-root missing");
if (!html.includes("干活中")) throw new Error("running label missing");
console.log("RENDER OK");
