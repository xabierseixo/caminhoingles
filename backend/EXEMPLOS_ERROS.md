# Exemplo de respostas de erro do backend Flask

## Erro de autenticación (token incorrecto ou expirado)
```json
{
  "success": false,
  "error": "Token de autenticación incorrecto ou expirado",
  "status_code": 401,
  "details": {}
}
```

## Erro de parámetros incorrectos
```json
{
  "success": false,
  "error": "Parámetros incorrectos na petición",
  "status_code": 400,
  "details": {"param": ["mensaxe de erro"]}
}
```

## API caída ou sen resposta
```json
{
  "success": false,
  "error": "Erro de conexión coa API externa (API caída ou sen resposta)",
  "status_code": 502,
  "details": "mensaxe de excepción"
}
```
