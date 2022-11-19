module.exports = {
  apps : [{
    name   : 'GHWHOOK',
    script : './app.py',
    interpreter: '/usr/bin/python3',
    env: {
      SECRET_TOKEN: '', // Edit this
      GIT_PATH: '', // Set this
      PORT: '8080',
      HOST: '127.0.0.1',
    }
  }]
}
