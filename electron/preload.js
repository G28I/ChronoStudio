/**
 * electron/preload.js — Secure Context Bridge Preload
 * Context isolation: ENABLED
 * Node integration: DISABLED
 * Exposes strictly validated, scoped APIs to the renderer window.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  getAppVersion: () => ipcRenderer.invoke('app:version'),
  getServerPort: () => ipcRenderer.invoke('app:server-port'),
  getBackendStatus: () => ipcRenderer.invoke('backend:status'),
  onBackendCrash: (callback) => {
    ipcRenderer.on('backend:crashed', (_event, data) => callback(data));
  },
  onBackendRestarted: (callback) => {
    ipcRenderer.on('backend:restarted', (_event, data) => callback(data));
  }
});
