# Benchmarks for event-based monitoring stores

[TODO: Add link to blog explaining the project]


## Setting up the infra

**NOTE**: Some terraform configurations use private modules built by Elucidata. They
have been obscured. You will need to replace them with equivalent resources from
official AWS terraform provider or use modules from other providers.

The infra can be provisioned through terraform. To do so, run the following commands:
```bash
cd infra
terraform init
terraform apply
```
This should create all the data stores as well as the benchmarking Lambdas and DynamoDB.


## Deploying to Lambda

To generate Lambda layer and Lambda source code bundles, execute the following:
```bash
python zip_lambda_layer.py
python zip_lambda_code.py
```
Deploy the above to Lambda layers and the reader and writer Lambdas using your preferred
method. I used AWS CLI (too lazy to setup CI :)


## Performing the benchmark

Adjust the number of iterations (decides cumulative scale) and the run the script:
```bash
python run.py
```
This will invoke the two Lambdas periodically to generate events as well as query them.
