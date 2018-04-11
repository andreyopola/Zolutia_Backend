#!/usr/bin/env bash
rm manage.py commit
cd app
mkdir app
mv * app/
mv app/app.py main.py
mv ../requirements.txt .
cd ..
echo "if __name__ == \"__main__\":" >> app/main.py
echo "    app.run(host='0.0.0.0', debug=True, port=80)" >> app/main.py
docker build -t gcr.io/copper-oven-193619/zol-backend:test --no-cache -f Dockerfile-test .
gcloud docker -- push gcr.io/copper-oven-193619/zol-backend:test
