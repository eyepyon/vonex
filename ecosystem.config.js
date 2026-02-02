module.exports = {
  apps: [{
    name: 'vonexapp',
    script: 'main.py',
    interpreter: 'python3',
    cwd: '/var/www/vonex',
    env: {
      // .envファイルから読み込まれます
    },
    watch: false,
    max_memory_restart: '500M',
    error_file: '/var/www/vonex/logs/error.log',
    out_file: '/var/www/vonex/logs/out.log',
    log_file: '/var/www/vonex/logs/combined.log',
    time: true
  }]
};
