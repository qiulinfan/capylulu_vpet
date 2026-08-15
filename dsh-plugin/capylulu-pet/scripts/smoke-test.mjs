// Smoke-test the built client bundle: emulate the browser loader, resolve
// react from the web profile's node_modules, and verify the plugin contract.
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const bundlePath = "C:/Users/rynne/Desktop/capylulu_vpet/dsh-plugin/capylulu-pet/lib/client.js";
const profileModules = "C:/Users/rynne/.dsh/profiles/web/node_modules";

const source = readFileSync(bundlePath, "utf8");
if (!source.startsWith("window.__ModuleLoader__.load(")) {
  throw new Error("bundle does not start with window.__ModuleLoader__.load(");
}

const registrations = [];
const sandbox = {
  window: {
    __ModuleLoader__: {
      load(entry) {
        registrations.push(entry);
      },
    },
  },
  matchMedia: undefined,
  Image: undefined,
  document: undefined,
  setTimeout,
  clearTimeout,
  Date,
  Math,
  Symbol,
  Object,
  Array,
  JSON,
  console,
};
vm.createContext(sandbox);
vm.runInContext(source, sandbox, { filename: "client.js" });

const entry = registrations[0];
if (!entry || entry.id !== "capylulu-pet") {
  throw new Error("bad entry: " + JSON.stringify(entry));
}
if (typeof entry.factory !== "function") throw new Error("factory missing");

const requireFromProfile = createRequire(profileModules + "/x.js");
const result = entry.factory(requireFromProfile);

console.log("exports:", Object.keys(result));
if (typeof result.apply !== "function") throw new Error("apply missing");
if (!Array.isArray(result.inject) || result.inject.join(",") !== "slots") {
  throw new Error("inject mismatch: " + JSON.stringify(result.inject));
}

// run apply() with a captured slots service
let capturedOptions = null;
let registered = null;
let disposed = 0;
const fakeSlots = {
  register(options, component) {
    capturedOptions = options;
    registered = component;
    return () => {
      disposed++;
    };
  },
};
const applyCtx = {
  slots: fakeSlots,
  effect(fn) {
    const dispose = fn();
    if (typeof dispose === "function") dispose();
  },
};
result.apply(applyCtx);
console.log("register options:", JSON.stringify(capturedOptions));
console.log("registered component type:", typeof registered);
console.log("disposed:", disposed);
if (capturedOptions.name !== "shell.overlay") throw new Error("wrong slot name");
if (typeof registered !== "function") throw new Error("component not a function");
console.log("SMOKE OK");
