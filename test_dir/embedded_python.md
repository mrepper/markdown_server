## Section 1 -- Embedded python
```python
import click

@click.command()
@click.argument("arg1")
@click.argument("arg2")
def main(arg1, arg2):
    print(f"arg1: '{arg1}'")
    print(f"arg2: '{arg2}'")

if __name__ == "__main__":
    main()
```
