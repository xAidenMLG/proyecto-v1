// Cliente de la API local de DMD STUDIO.
// Errores HTTP → objeto {error, ...} con throw; el llamador decide cómo mostrarlos.

async function req(method, url, body) {
  const opt = { method, headers: {} };
  if (body !== undefined) {
    opt.headers['Content-Type'] = 'application/json';
    opt.body = JSON.stringify(body);
  }
  let r;
  try {
    r = await fetch(url, opt);
  } catch (e) {
    throw { error: 'no se pudo contactar con el servidor local (' + e.message + ')' };
  }
  let data = null;
  const ct = r.headers.get('content-type') || '';
  if (ct.includes('application/json')) {
    try { data = await r.json(); } catch { data = null; }
  }
  if (!r.ok) {
    throw (data && typeof data === 'object') ? data : { error: 'HTTP ' + r.status + ' ' + r.statusText };
  }
  return data;
}

export const API = {
  capabilities: () => req('GET', '/api/capabilities'),
  system: () => req('GET', '/api/system'),
  getSettings: () => req('GET', '/api/settings'),
  putSettings: (p) => req('PUT', '/api/settings', p),

  projects: () => req('GET', '/api/projects'),
  project: (pid) => req('GET', '/api/projects/' + pid),
  createProject: (b) => req('POST', '/api/projects', b),
  saveProject: (pid, b) => req('PUT', '/api/projects/' + pid, b),
  duplicateProject: (pid, name) => req('POST', '/api/projects/' + pid + '/duplicate', name ? { name } : {}),
  deleteProject: (pid) => req('DELETE', '/api/projects/' + pid),
  exportUrl: (pid) => '/api/projects/' + pid + '/export',

  validate: (doc) => req('POST', '/api/validate', { doc }),
  compilePreview: (doc) => req('POST', '/api/compile-preview', { doc }),

  generate: (pid, b) => req('POST', '/api/projects/' + pid + '/generate', b),
  job: (jid) => req('GET', '/api/jobs/' + jid),
  jobs: (pid) => req('GET', '/api/jobs' + (pid ? '?pid=' + pid : '')),
  cancelJob: (jid) => req('POST', '/api/jobs/' + jid + '/cancel'),

  generation: (pid, gid) => req('GET', '/api/projects/' + pid + '/generations/' + gid),
  genFileUrl: (pid, gid, f) => '/api/projects/' + pid + '/generations/' + gid + '/files/' + f,
  genLogUrl: (pid, gid) => '/api/projects/' + pid + '/generations/' + gid + '/logfile',
  audioUrl: (pid, gid, out, f) => '/api/projects/' + pid + '/audio/' + gid + '/' + out + '/' + f,
};
