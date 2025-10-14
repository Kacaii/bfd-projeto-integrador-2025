#   Liste os comandos disponíveis
@default:
    just --list

alias r := run

# 󰒋  Inicie o servidor
run:
    poetry run main

alias t := test

# 󰙨 Inicie os testes unitários
test:
    poetry run pytest
