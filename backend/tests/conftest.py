import os
import tempfile

# Os testes usam um banco SQLite temporário, nunca o banco de desenvolvimento.
# Precisa ser definido antes de qualquer import de app.config.
_banco = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_banco.name}"
os.environ["POPULAR_BANCO_SE_VAZIO"] = "true"
