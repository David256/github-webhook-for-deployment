# Github Webhook for deployment

A Python tool that listens for Webhook events from Github to use PM2 and do the deployment.

**Take in mind:**

The `SECRET_TOKEN` value goes in _repository settings > Webhooks > Add webhook: **Secret** field_.

# Basis code:
- @andrewfraley (for this [gist](https://gist.github.com/andrewfraley/0229f59a11d76373f11b5d9d8c6809bc))
- @baylf2000 & @insomnes (for having sent & answered this [issue](https://github.com/tiangolo/fastapi/issues/4321))
