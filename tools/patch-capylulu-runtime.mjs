#!/usr/bin/env node
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const PATCH_ID = "capylulu-idle-v1";
const PATCH_MARKER = "capyluluRuntimePatch";
const BLOCK_SIZE = 4 * 1024 * 1024;

function usage() {
  console.log(`Usage:
  node tools/patch-capylulu-runtime.mjs --check [--asar PATH]
  node tools/patch-capylulu-runtime.mjs --output PATH [--asar PATH]
  node tools/patch-capylulu-runtime.mjs --apply [--asar PATH]
  node tools/patch-capylulu-runtime.mjs --restore [--asar PATH] [--backup PATH]

Options:
  --asar PATH         Codex app.asar path. Auto-detected on Windows when omitted.
  --output PATH       Write a patched app.asar copy to PATH.
  --apply             Replace the target app.asar after writing a backup.
  --restore           Restore the latest backup, or the backup passed with --backup.
  --backup PATH       Backup file to restore.
  --backup-root PATH  Backup/output directory. Defaults to ~/.codex/capylulu-runtime-backups.
  --check             Print current runtime patch status.
  --help              Show this help.
`);
}

function parseArgs(argv) {
  const args = {
    apply: false,
    asar: process.env.CAPYLULU_CODEX_ASAR || "",
    backup: "",
    backupRoot: path.join(os.homedir(), ".codex", "capylulu-runtime-backups"),
    check: false,
    output: "",
    restore: false,
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--help" || arg === "-h") {
      usage();
      process.exit(0);
    }
    if (arg === "--apply") {
      args.apply = true;
      continue;
    }
    if (arg === "--check") {
      args.check = true;
      continue;
    }
    if (arg === "--restore") {
      args.restore = true;
      continue;
    }
    if (arg === "--asar" || arg === "--output" || arg === "--backup" || arg === "--backup-root") {
      const value = argv[++i];
      if (!value) {
        throw new Error(`${arg} needs a value`);
      }
      const key = arg.slice(2).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      args[key] = value;
      continue;
    }
    throw new Error(`Unknown option: ${arg}`);
  }

  return args;
}

function normalizePath(value) {
  return path.resolve(value).replace(/\\/g, "/");
}

function findDefaultAsar() {
  if (process.platform !== "win32") {
    throw new Error("--asar is required outside Windows");
  }

  const processCandidates = findAsarFromRunningCodex();
  if (processCandidates.length > 0) {
    return processCandidates[0];
  }

  const roots = [
    path.join(process.env.ProgramFiles || "C:/Program Files", "WindowsApps"),
    process.env.LOCALAPPDATA ? path.join(process.env.LOCALAPPDATA, "Programs") : "",
  ].filter(Boolean);

  const candidates = [];
  for (const root of roots) {
    if (!fs.existsSync(root)) {
      continue;
    }
    let entries = [];
    try {
      entries = fs.readdirSync(root, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      if (!entry.isDirectory() || !entry.name.startsWith("OpenAI.Codex_")) {
        continue;
      }
      const asarPath = path.join(root, entry.name, "app", "resources", "app.asar");
      if (fs.existsSync(asarPath)) {
        candidates.push({
          mtimeMs: fs.statSync(asarPath).mtimeMs,
          path: asarPath,
        });
      }
    }
  }

  candidates.sort((a, b) => b.mtimeMs - a.mtimeMs);
  if (candidates.length === 0) {
    throw new Error("Could not auto-detect Codex app.asar. Pass --asar PATH.");
  }
  return candidates[0].path;
}

function findAsarFromRunningCodex() {
  const script = "Get-Process Codex,codex -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Path -Unique";
  let output = "";
  try {
    output = execFileSync("powershell.exe", ["-NoProfile", "-Command", script], {
      encoding: "utf8",
      windowsHide: true,
    });
  } catch {
    return [];
  }

  return output
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((exePath) => path.join(path.dirname(exePath), "resources", "app.asar"))
    .filter((asarPath, index, all) => fs.existsSync(asarPath) && all.indexOf(asarPath) === index);
}

function align4(value) {
  return value + ((4 - (value % 4)) % 4);
}

function readArchiveHeader(asarPath) {
  const fd = fs.openSync(asarPath, "r");
  try {
    const sizePickle = Buffer.alloc(8);
    fs.readSync(fd, sizePickle, 0, sizePickle.length, 0);
    const sizePayload = sizePickle.readUInt32LE(0);
    if (sizePayload !== 4) {
      throw new Error(`Unexpected asar size pickle payload: ${sizePayload}`);
    }

    const headerSize = sizePickle.readUInt32LE(4);
    const headerPickle = Buffer.alloc(headerSize);
    fs.readSync(fd, headerPickle, 0, headerSize, 8);

    const headerPayload = headerPickle.readUInt32LE(0);
    if (headerPickle.length - headerPayload !== 4) {
      throw new Error("Unsupported asar header pickle layout");
    }

    const jsonLength = headerPickle.readInt32LE(4);
    const headerString = headerPickle.toString("utf8", 8, 8 + jsonLength);
    return {
      dataOffset: 8 + headerSize,
      header: JSON.parse(headerString),
      headerSize,
      headerString,
    };
  } finally {
    fs.closeSync(fd);
  }
}

function encodeArchiveHeader(header, headerSize) {
  const headerString = JSON.stringify(header);
  const jsonLength = Buffer.byteLength(headerString, "utf8");
  const payloadSize = headerSize - 4;
  const requiredPayload = 4 + align4(jsonLength);
  if (requiredPayload > payloadSize) {
    throw new Error(
      `Patched asar header is too large by ${requiredPayload - payloadSize} bytes.`
    );
  }

  const buffer = Buffer.alloc(headerSize);
  buffer.writeUInt32LE(payloadSize, 0);
  buffer.writeInt32LE(jsonLength, 4);
  buffer.write(headerString, 8, jsonLength, "utf8");
  return buffer;
}

function walkFiles(node, prefix = "", output = []) {
  if (!node || !node.files) {
    return output;
  }
  for (const [name, child] of Object.entries(node.files)) {
    const childPath = prefix ? `${prefix}/${name}` : name;
    if (child.files) {
      walkFiles(child, childPath, output);
    } else {
      output.push({ path: childPath, node: child });
    }
  }
  return output;
}

function readPackedFile(asarPath, headerInfo, fileNode) {
  if (fileNode.unpacked) {
    throw new Error("The avatar runtime is unexpectedly unpacked.");
  }
  const size = Number(fileNode.size);
  const offset = headerInfo.dataOffset + Number(fileNode.offset);
  const buffer = Buffer.alloc(size);
  const fd = fs.openSync(asarPath, "r");
  try {
    fs.readSync(fd, buffer, 0, size, offset);
  } finally {
    fs.closeSync(fd);
  }
  return buffer;
}

function findAvatarRuntime(asarPath, headerInfo) {
  const candidates = walkFiles(headerInfo.header)
    .filter((file) => /^webview\/assets\/codex-avatar-.*\.js$/.test(file.path));

  for (const file of candidates) {
    const source = readPackedFile(asarPath, headerInfo, file.node).toString("utf8");
    if (
      source.includes("loopStartIndex") &&
      source.includes("P={failed:") &&
      source.includes("function I(e,t)")
    ) {
      return { ...file, source };
    }
  }

  throw new Error("Could not find the Codex avatar runtime JS in app.asar.");
}

function integrityForBuffer(buffer) {
  const hash = crypto.createHash("sha256").update(buffer).digest("hex");
  const blocks = [];
  for (let offset = 0; offset < buffer.length; offset += BLOCK_SIZE) {
    blocks.push(
      crypto.createHash("sha256").update(buffer.subarray(offset, offset + BLOCK_SIZE)).digest("hex")
    );
  }
  if (buffer.length === 0) {
    blocks.push(crypto.createHash("sha256").update(buffer).digest("hex"));
  }
  return { algorithm: "SHA256", blockSize: BLOCK_SIZE, blocks, hash };
}

function patchAvatarRuntime(source) {
  let patched = source.replace(/k=8,A=9,j=(?:6|4),M=\[/, "k=8,A=9,j=4,M=[");

  if (patched.includes(PATCH_MARKER)) {
    return { patched, changed: patched !== source };
  }

  const start = patched.indexOf("function F(e){");
  const end = patched.indexOf("function I(e,t){", start);
  if (start < 0 || end < 0) {
    throw new Error("Avatar runtime shape changed; could not patch function F.");
  }

  const replacement = 'function F(e){let t=(0,h.c)(6),{avatarRef:n,isAnimationEnabled:r,prefersReducedMotion:i,state:a}=e,o=r===void 0?!0:r,s=a===void 0?`idle`:a,c,l;t[0]!==n||t[1]!==o||t[2]!==i||t[3]!==s?(c=()=>{let e=n.current;if(e==null)return;let t=I(s,i||!o),r=t.frames,a=0,c=null,f=0,p=s===`idle`&&!i&&o;if(e.dataset.capyluluRuntimePatch=`1`,e.style.backgroundPosition=R(r[a]),r.length===1)return;let u=()=>{c=window.setTimeout(()=>{let n=a+1;if(n>=r.length){if(p){let o=r===t.frames;o&&(f++);if(f>=15){r=[...P.failed,...P.failed,...P.failed],a=0,e.style.backgroundPosition=R(r[a]),u();return}if(o&&f>0&&f%5===0){let t=[P.running,P.idle,P.waiting][Math.floor(Math.random()*3)];r=[...t,...N],a=0,e.style.backgroundPosition=R(r[a]),u();return}r=t.frames}if(t.loopStartIndex!=null){a=t.loopStartIndex,e.style.backgroundPosition=R(r[a]),u();return}c=null;return}a=n,e.style.backgroundPosition=R(r[a]),u()},r[a].frameDurationMs)};return u(),()=>{c!=null&&window.clearTimeout(c)}},l=[n,o,i,s],t[0]=n,t[1]=o,t[2]=i,t[3]=s,t[4]=c,t[5]=l):(c=t[4],l=t[5]),(0,d.useEffect)(c,l)}';

  patched = `${patched.slice(0, start)}${replacement}${patched.slice(end)}`;
  return { patched, changed: patched !== source };
}

function patchAsar(inputAsar, outputAsar) {
  const headerInfo = readArchiveHeader(inputAsar);
  const avatar = findAvatarRuntime(inputAsar, headerInfo);
  const { patched, changed } = patchAvatarRuntime(avatar.source);
  const patchedBuffer = Buffer.from(patched, "utf8");

  fs.mkdirSync(path.dirname(outputAsar), { recursive: true });
  if (fs.existsSync(outputAsar)) {
    fs.rmSync(outputAsar, { force: true });
  }
  fs.copyFileSync(inputAsar, outputAsar);

  const appendOffset = fs.statSync(outputAsar).size;
  avatar.node.offset = String(appendOffset - headerInfo.dataOffset);
  avatar.node.size = patchedBuffer.length;
  avatar.node.integrity = integrityForBuffer(patchedBuffer);

  let integrityRemoved = false;
  let headerBuffer;
  try {
    headerBuffer = encodeArchiveHeader(headerInfo.header, headerInfo.headerSize);
  } catch (error) {
    if (!(error instanceof Error) || !error.message.includes("too large")) {
      throw error;
    }
    delete avatar.node.integrity;
    integrityRemoved = true;
    headerBuffer = encodeArchiveHeader(headerInfo.header, headerInfo.headerSize);
  }
  const fd = fs.openSync(outputAsar, "r+");
  try {
    fs.writeSync(fd, headerBuffer, 0, headerBuffer.length, 8);
    fs.writeSync(fd, patchedBuffer, 0, patchedBuffer.length, appendOffset);
  } finally {
    fs.closeSync(fd);
  }

  return {
    avatarFile: avatar.path,
    changed,
    idleDurationScale: "4x base frame durations (1.5x faster than Codex default 6x)",
    integrityRemoved,
    outputAsar,
    patchId: PATCH_ID,
  };
}

function checkAsar(asarPath) {
  const headerInfo = readArchiveHeader(asarPath);
  const avatar = findAvatarRuntime(asarPath, headerInfo);
  const jMatch = avatar.source.match(/k=8,A=9,j=(\d+),M=\[/);
  return {
    asar: asarPath,
    avatarFile: avatar.path,
    hasPatchMarker: avatar.source.includes(PATCH_MARKER),
    idleDurationMultiplier: jMatch ? Number(jMatch[1]) : null,
    patched: avatar.source.includes(PATCH_MARKER) && jMatch?.[1] === "4",
  };
}

function sha256File(filePath) {
  const hash = crypto.createHash("sha256");
  const fd = fs.openSync(filePath, "r");
  const buffer = Buffer.alloc(1024 * 1024);
  try {
    let bytesRead = 0;
    do {
      bytesRead = fs.readSync(fd, buffer, 0, buffer.length, null);
      if (bytesRead > 0) {
        hash.update(buffer.subarray(0, bytesRead));
      }
    } while (bytesRead > 0);
  } finally {
    fs.closeSync(fd);
  }
  return hash.digest("hex");
}

function newestBackup(backupRoot) {
  if (!fs.existsSync(backupRoot)) {
    return "";
  }
  const backups = fs.readdirSync(backupRoot)
    .filter((name) => name.endsWith(".bak") && name.startsWith("app.asar."))
    .map((name) => path.join(backupRoot, name))
    .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  return backups[0] || "";
}

function restoreBackup(targetAsar, backupPath) {
  if (!backupPath || !fs.existsSync(backupPath)) {
    throw new Error("No backup found to restore.");
  }
  fs.copyFileSync(backupPath, targetAsar);
  return { restoredFrom: backupPath, targetAsar };
}

function canOpenForWrite(filePath) {
  try {
    const fd = fs.openSync(filePath, "r+");
    fs.closeSync(fd);
    return true;
  } catch {
    return false;
  }
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const targetAsar = normalizePath(args.asar || findDefaultAsar());
  const backupRoot = normalizePath(args.backupRoot);
  fs.mkdirSync(backupRoot, { recursive: true });

  if (args.check) {
    console.log(JSON.stringify(checkAsar(targetAsar), null, 2));
    return;
  }

  if (args.restore) {
    const backupPath = normalizePath(args.backup || newestBackup(backupRoot));
    console.log(JSON.stringify(restoreBackup(targetAsar, backupPath), null, 2));
    return;
  }

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const outputAsar = normalizePath(args.output || path.join(backupRoot, `app.asar.${PATCH_ID}.${timestamp}.patched`));
  const result = patchAsar(targetAsar, outputAsar);

  if (args.apply) {
    if (!canOpenForWrite(targetAsar)) {
      console.error(JSON.stringify({
        ...result,
        applied: false,
        reason: "Target app.asar is not writable. On MSIX WindowsApps installs this usually requires an elevated/owned package directory.",
      }, null, 2));
      process.exitCode = 3;
      return;
    }

    const sourceHash = sha256File(targetAsar).slice(0, 16);
    const backupPath = path.join(backupRoot, `app.asar.${sourceHash}.${timestamp}.bak`);
    fs.copyFileSync(targetAsar, backupPath);
    fs.copyFileSync(outputAsar, targetAsar);
    console.log(JSON.stringify({
      ...result,
      applied: true,
      backupPath: normalizePath(backupPath),
      targetAsar,
      verification: checkAsar(targetAsar),
    }, null, 2));
    return;
  }

  console.log(JSON.stringify({
    ...result,
    applied: false,
    verification: checkAsar(outputAsar),
  }, null, 2));
}

try {
  main();
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
