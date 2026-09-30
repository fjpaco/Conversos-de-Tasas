# Conversor USD, MXN, CLP y UF

Conversor web con tasas que se actualizan solas todos los días mediante GitHub Actions.

## Qué hay en este repositorio

| Archivo | Para qué sirve |
|---|---|
| `index.html` | El conversor. Lee `tasas.json` al abrirse, cada hora y con "Actualizar ahora". |
| `tasas.json` | Las tasas vigentes. Lo reescribe el robot de GitHub; no hace falta tocarlo. |
| `scripts/update_rates.py` | Descarga UF, dólar observado y USD/MXN y escribe `tasas.json`. |
| `.github/workflows/update-rates.yml` | Programa el script a las 7:00 y 13:00 (hora de Querétaro). |

## Puesta en marcha

1. Crea una cuenta en github.com si no tienes.
2. Crea un repositorio nuevo, por ejemplo `conversor-tasas`, marcado como **Public** (GitHub Pages gratis requiere repositorio público). No agregues README.
3. En la página del repositorio vacío, elige **uploading an existing file** y arrastra el contenido de esta carpeta: `index.html`, `tasas.json`, `README.md` y las carpetas `scripts` y `.github`. Haz clic en **Commit changes**.
   - La carpeta `.github` empieza con punto y en Windows o Mac puede estar oculta. Si no se subió, crea el archivo a mano: **Add file → Create new file**, escribe como nombre `.github/workflows/update-rates.yml` y pega el contenido.
4. Ve a **Settings → Actions → General → Workflow permissions**, marca **Read and write permissions** y guarda.
5. Ve a **Settings → Pages**. En *Source* elige **Deploy from a branch**, rama **main**, carpeta **/(root)**, y guarda. En uno o dos minutos aparece la dirección: `https://TU-USUARIO.github.io/conversor-tasas/`.
6. Ve a **Actions**, entra a **Actualizar tasas** y presiona **Run workflow** para la primera descarga. Cuando termine en verde, abre tu dirección de Pages.

## Opcional: FIX oficial de Banxico

1. Pide un token gratis en https://www.banxico.org.mx/SieAPIRest/service/v1/token
2. En el repositorio: **Settings → Secrets and variables → Actions → New repository secret**.
3. Nombre: `BANXICO_TOKEN`. Valor: tu token.

Desde la siguiente corrida, USD/MXN usará el FIX en lugar del tipo de cambio de mercado.

## Uso diario

- La página muestra cuándo se actualizaron las tasas en el servidor.
- "Actualizar ahora" vuelve a leer `tasas.json` sin esperar.
- Para forzar una descarga nueva en el servidor, usa el enlace "Forzar actualización en GitHub" (o Actions → Run workflow) y recarga en dos o tres minutos.
- Para instalarla como app: ábrela en Chrome o Edge y usa "Instalar" desde el menú o la barra de direcciones.
