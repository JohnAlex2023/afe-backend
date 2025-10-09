# Script de PowerShell para corregir el frontend
# Ejecutar desde: C:\Users\jhont\PRIVADO_ODO\afe-backend

$frontendFile = "C:\Users\jhont\PRIVADO_ODO\afe_frontend\src\features\dashboard\DashboardPage.tsx"

Write-Host "🔧 Corrigiendo archivo del frontend..." -ForegroundColor Cyan

# Leer el contenido del archivo
$content = Get-Content $frontendFile -Raw

# Corrección 1: Cambiar la llamada al API para admin
$content = $content -replace `
  'const \[todasResponse, asignadasResponse\] = await Promise\.all\(\[\s*apiClient\.get\(''/facturas/''\),.*?apiClient\.get\(''/facturas/'',.*?\{ params: \{ solo_asignadas: true \} \}\),', `
  'const [todasResponse, asignadasResponse] = await Promise.all([
          apiClient.get(''/facturas/'', { params: { page: 1, per_page: 2000 } }), // Todas las facturas
          apiClient.get(''/facturas/'', { params: { solo_asignadas: true, page: 1, per_page: 2000 } }), // Solo asignadas'

# Corrección 2: Extraer data del response
$content = $content -replace `
  'setTotalTodasFacturas\(todasResponse\.data\.length\);(\s*)setTotalAsignadas\(asignadasResponse\.data\.length\);(\s*)// Usar los datos según la vista seleccionada(\s*)const allFacturas = vistaFacturas === ''todas'' \? todasResponse\.data : asignadasResponse\.data;', `
  '// ✅ CORRECCIÓN: Ahora el backend devuelve { data: [...], pagination: {...} }
        const todasFacturasData = todasResponse.data.data || [];
        const asignadasData = asignadasResponse.data.data || [];

        setTotalTodasFacturas(todasResponse.data.pagination?.total || todasFacturasData.length);
        setTotalAsignadas(asignadasResponse.data.pagination?.total || asignadasData.length);

        // Usar los datos según la vista seleccionada
        const allFacturas = vistaFacturas === ''todas'' ? todasFacturasData : asignadasData;'

# Corrección 3: Para responsable
$content = $content -replace `
  '// Responsable solo ve sus facturas asignadas(\s*)const response = await apiClient\.get\(''/facturas/''\);(\s*)const allFacturas = response\.data;(\s*)setTotalAsignadas\(allFacturas\.length\);(\s*)setTotalTodasFacturas\(allFacturas\.length\);', `
  '// Responsable solo ve sus facturas asignadas
        const response = await apiClient.get(''/facturas/'', { params: { page: 1, per_page: 2000 } });

        // ✅ CORRECCIÓN: Ahora el backend devuelve { data: [...], pagination: {...} }
        const allFacturas = response.data.data || [];

        setTotalAsignadas(response.data.pagination?.total || allFacturas.length);
        setTotalTodasFacturas(response.data.pagination?.total || allFacturas.length); // Para responsable es lo mismo'

# Corrección 4: Agregar función handleExport si no existe
if ($content -notmatch 'const handleExport') {
    $content = $content -replace `
      '(const handleReject = async \(factura: Factura\) => \{[^}]*\}\);)', `
      '$1

  const handleExport = () => {
    // Construir URL de exportación
    const params = new URLSearchParams();

    if (filterEstado !== ''todos'') {
      params.append(''estado'', filterEstado);
    }

    if (user?.rol === ''admin'' && vistaFacturas === ''asignadas'') {
      params.append(''solo_asignadas'', ''true'');
    }

    // Descargar CSV
    const url = `/facturas/export/csv${params.toString() ? ''?'' + params.toString() : ''''}`;
    window.location.href = apiClient.defaults.baseURL + url;
  };'
}

# Corrección 5: Agregar onClick al botón de exportar (Admin)
$content = $content -replace `
  '(<Button\s+fullWidth\s+variant="outlined"\s+startIcon=\{<Download />\})\s+(sx=\{\{[^}]*height: 56,[^}]*\}\})\s+(>\s+Exportar\s+</Button>)', `
  '$1
                    onClick={handleExport}
                    $2
                    $3'

# Guardar el archivo corregido
$content | Set-Content $frontendFile -NoNewline

Write-Host "✅ Archivo corregido exitosamente!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Cambios aplicados:" -ForegroundColor Yellow
Write-Host "  1. API calls actualizados para recibir { data, pagination }" -ForegroundColor White
Write-Host "  2. Extracción correcta de datos del response" -ForegroundColor White
Write-Host "  3. Función handleExport agregada" -ForegroundColor White
Write-Host "  4. Botón Exportar conectado" -ForegroundColor White
Write-Host ""
Write-Host "🔄 Ahora recarga el navegador (Ctrl + Shift + R)" -ForegroundColor Cyan
