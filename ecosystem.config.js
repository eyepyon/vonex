const fs = require('fs');
const path = require('path');

// .envファイルを読み込む
function loadEnv() {
  const envPath = path.join(__dirname, '.env');
  const env = {};
  
  if (fs.existsSync(envPath)) {
    const content = fs.readFileSync(envPath, 'utf8');
    content.split('\n').forEach(line => {
      // コメントと空行をスキップ
      if (line.trim() && !line.startsWith('#')) {
        const [key, ...valueParts] = line.split('=');
        if (key && valueParts.length > 0) {
          env[key.trim()] = valueParts.join('=').trim();
        }
      }
    });
  }
  
  return env;
}

module.exports = {
  apps: [{
    name: 'vonexapp',
    script: 'main.py',
    interpreter: '/var/www/vonex/venv/bin/python3',
    cwd: '/var/www/vonex',
    env: loadEnv(),
    watch: false,
    max_memory_restart: '500M',
    error_file: '/var/www/vonex/logs/error.log',
    out_file: '/var/www/vonex/logs/out.log',
    log_file: '/var/www/vonex/logs/combined.log',
    time: true
  }]
};
