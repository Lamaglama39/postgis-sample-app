#!/bin/bash

# Backend
cd backend/lambda;
bash create_zip.sh;

cd ../;
terraform init;
terraform apply -auto-approve;

bash update_env.sh;

# Frontend
cd ../frontend/app;
npm install;
npm run build;

cd ../terraform;
terraform init;
terraform apply -auto-approve;
