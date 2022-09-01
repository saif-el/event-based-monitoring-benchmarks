import json
import sys
import time

import boto3

client = boto3.client('lambda')
writer_lambda_name = 'dataplatform-play-monitoring-events-writer-v1'
reader_lambda_name = 'dataplatform-play-monitoring-events-reader-v1'


def _write(num_runs_per_iter):
    runs_this_iter = 0
    for i in range(num_runs_per_iter):
        try:
            client.invoke(
                FunctionName=writer_lambda_name,
                InvocationType='Event',
                LogType='None',
            )
            runs_this_iter = i + 1
            print(f"Triggered {runs_this_iter} runs", end="\r")
            time.sleep(900)
        except:
            print("Error while attempting to invoke writer Lambda")
            sys.exit(1)

    print(f"Triggered {runs_this_iter} runs")


def _read(scale):
    try:
        client.invoke(
            FunctionName=reader_lambda_name,
            InvocationType='Event',
            LogType='None',
            Payload=json.dumps({"scale": scale})
        )
        print("Triggered querying")
        time.sleep(420)
    except Exception as e:
        print("Error while attempting to invoke reader Lambda")
        sys.exit(1)


def main():
    num_runs_per_iter = 10
    target_num_iters = 8
    current_iter = 0
    while current_iter < target_num_iters:
        _write(num_runs_per_iter)
        current_iter += 1
        scale = f"{current_iter}x"
        _read(scale)


if __name__ == "__main__":
    main()
