import os


def main():
    repo_name = os.getcwd().split('/')[-1]
    os.system(
        "zip -qq -r ./{}.zip . -x '*.git*' -x 'infra*' -x 'venv*'".format(repo_name)
    )
    print("Source code was packed in {}.zip".format(repo_name))


if __name__ == '__main__':
    main()
