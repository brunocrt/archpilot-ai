mkdir -p data/uploads 
mkdir -p data/samples
podman compose -f .\infra\docker-compose.yml up --build