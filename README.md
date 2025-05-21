# ollama-k8s-RPi

Ollama AI Deployment on Kubernetes (Raspberry Pi)


## Ollama Backend

The Kubernetes deployment is found in the 'ollama' directory.  The ollama service will need to be launched first, and the models pulled.  The pull-ollama-models-job.yaml file will pull the models specified in that file.

```
kubectl apply -f ollama/k8s
```


## Discord Bridge

The Discord Bridge is a python program designed to run as a bot for the discord server.  First supply Kubernetes with your discord secret and then run the discord bridge.  This discord bot is designed to respond to messages that are preceded by `!ask` or tagging the bot's name (ToPaKi).

```
cd discord-bridge
make  # (or make rebuild)
kubectl create secret generic discord-token --from-literal=DISCORD_TOKEN="$DISCORD_TOKEN"
kubectl apply -f k8s
cd -
```

## Testing

Kubernetes jobs for testing ollama deployment with different models can be found in the `qa` directory.  I also did manual testing of different models out-of-the-box, the results of which can be found in **MANUAL_TESTING.md**.

