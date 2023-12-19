import docker

client = docker.from_env()

response = client.containers.run("python:3.8-slim", "echo 'Hello from Docker!'", stdout=True, stderr=True)

print(response.decode('utf-8'))  # Dekodowanie odpowiedzi z bytes do str