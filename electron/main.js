/**
 * electron/main.js — ChronoStudio Standalone Desktop Electron Shell
 * 
 * Security Guardrails:
 * - nodeIntegration: false
 * - contextIsolation: true
 * - sandbox: true
 * 
 * Process Supervision:
 * - Dynamic port selection to prevent port conflicts
 * - Python app_server child process lifecycle management
 * - Healthcheck polling before UI presentation
 * - Crash detection, error logging, and restart handling
 * - Clean process tree termination on window close / quit
 */

const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const net = require('net');
const http = require('http');
const { spawn, execSync } = require('child_process');

let mainWindow = null;
let pythonProcess = null;
let serverPort = null;
let isQuitting = false;

// 1. Port Conflict Resolution: Find available TCP port
function findAvailablePort(startPort = 8080) {
  return new Promise((resolve, reject) => {
    function tryPort(p) {
      const s = net.createServer();
      s.once('error', (err) => {
        if (err.code === 'EADDRINUSE') {
          tryPort(p + 1);
        } else {
          reject(err);
        }
      });
      s.once('listening', () => {
        s.close(() => resolve(p));
      });
      s.listen(p, '127.0.0.1');
    }
    tryPort(startPort);
  });
}

// 2. Healthcheck: Poll HTTP server until ready
function waitForServerReady(port, maxAttempts = 30, intervalMs = 300) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    function check() {
      attempts++;
      const req = http.get(`http://127.0.0.1:${port}/api/status`, (res) => {
        if (res.statusCode === 200) {
          resolve(true);
        } else {
          retry();
        }
      });
      req.on('error', () => retry());
      req.setTimeout(500, () => {
        req.destroy();
        retry();
      });
    }

    function retry() {
      if (attempts >= maxAttempts) {
        reject(new Error(`Backend failed to respond on port ${port} after ${maxAttempts * intervalMs}ms`));
      } else {
        setTimeout(check, intervalMs);
      }
    }

    check();
  });
}

// 3. Child Process Supervision
function startBackendServer(port) {
  const rootDir = path.resolve(__dirname, '..');
  const pythonScript = path.join(rootDir, 'app_server.py');
  
  console.log(`[Electron Supervisor] Launching backend server on port ${port}...`);
  pythonProcess = spawn('python', [pythonScript, '--port', String(port)], {
    cwd: rootDir,
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
    stdio: ['ignore', 'pipe', 'pipe']
  });

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Python Backend STDOUT] ${data.toString().trim()}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Python Backend STDERR] ${data.toString().trim()}`);
  });

  pythonProcess.on('exit', (code, signal) => {
    console.warn(`[Electron Supervisor] Backend process exited with code ${code}, signal ${signal}`);
    if (!isQuitting && mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('backend:crashed', { code, signal });
    }
  });

  pythonProcess.on('error', (err) => {
    console.error(`[Electron Supervisor] Failed to spawn backend process:`, err);
  });
}

// 4. Clean Process Tree Termination
function terminateBackendServer() {
  if (pythonProcess && pythonProcess.pid) {
    const pid = pythonProcess.pid;
    console.log(`[Electron Supervisor] Terminating backend process tree (PID: ${pid})...`);
    try {
      if (process.platform === 'win32') {
        execSync(`taskkill /pid ${pid} /T /F`);
      } else {
        pythonProcess.kill('SIGTERM');
      }
    } catch (e) {
      // Process may already have terminated
    }
    pythonProcess = null;
  }
}

// 5. Create Secure Browser Window
function createMainWindow(port) {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: 'ChronoStudio — OpenPremiere Desktop',
    backgroundColor: '#16161c',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  mainWindow.loadURL(`http://127.0.0.1:${port}/`);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC Handlers
ipcMain.handle('app:version', () => app.getVersion());
ipcMain.handle('app:server-port', () => serverPort);
ipcMain.handle('backend:status', async () => {
  if (!serverPort) return { online: false };
  try {
    return await new Promise((resolve) => {
      http.get(`http://127.0.0.1:${serverPort}/api/status`, (res) => {
        resolve({ online: res.statusCode === 200, port: serverPort });
      }).on('error', () => resolve({ online: false }));
    });
  } catch (e) {
    return { online: false, error: e.message };
  }
});

// App Lifecycle
app.whenReady().then(async () => {
  try {
    serverPort = await findAvailablePort(8080);
    startBackendServer(serverPort);
    await waitForServerReady(serverPort);
    createMainWindow(serverPort);
  } catch (err) {
    console.error('[Electron Startup Error]', err);
    dialog.showErrorBox('ChronoStudio Startup Failure', `Failed to start desktop backend:\n${err.message}`);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  isQuitting = true;
  terminateBackendServer();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  isQuitting = true;
  terminateBackendServer();
});
