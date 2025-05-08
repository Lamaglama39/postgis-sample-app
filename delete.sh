#!/bin/bash

# frontend
cd frontend/terraform/;
terraform destroy -auto-approve;

# backend
cd ../../backend/;
terraform destroy -auto-approve;
