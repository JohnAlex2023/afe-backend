# SOLUCIÓN PROFESIONAL: Alertas aria-hidden

**Problema:** Elementos con `aria-hidden="true"` contienen elementos focuseables
**Severidad:** Media (Accesibilidad)
**Componente:** Frontend React

---

## DIAGNÓSTICO

### Alerta Exact del navegador:
```
Blocked aria-hidden on an element because its descendant retained focus.
The focus must not be hidden from assistive technology users.
Avoid using aria-hidden on a focused element or its ancestor.
Consider using the inert attribute instead.
```

### Causa Raíz
El código frontend tiene elementos interactivos (botones, inputs) dentro de contenedores marcados como `aria-hidden="true"`. Esto crea un conflicto de accesibilidad.

---

## SOLUCIÓN 1: Usar inert en lugar de aria-hidden

**Archivo a modificar:** Frontend (probablemente en modal/dialog components)

**ANTES (problemático):**
```jsx
<div aria-hidden={!isOpen}>
  <button onClick={handleClick}>Click me</button>
</div>
```

**DESPUÉS (correcto):**
```jsx
<div inert={!isOpen ? "" : undefined}>
  <button onClick={handleClick}>Click me</button>
</div>
```

O simplemente:
```jsx
{isOpen && (
  <div>
    <button onClick={handleClick}>Click me</button>
  </div>
)}
```

---

## SOLUCIÓN 2: Deshabilitar focus en elementos ocultos

**ANTES:**
```jsx
<div aria-hidden="true">
  <button>Button</button>  {/* Problemático */}
  <input type="text" />    {/* Problemático */}
</div>
```

**DESPUÉS:**
```jsx
<div aria-hidden="true">
  <button tabIndex={-1}>Button</button>  {/* Correcto */}
  <input type="text" tabIndex={-1} />    {/* Correcto */}
</div>
```

---

## SOLUCIÓN 3: Usar Conditional Rendering

**Mejor práctica (recomendado):**
```jsx
// NO hacer esto:
<div className={isOpen ? "visible" : "hidden"} aria-hidden={!isOpen}>
  <button>Click</button>
</div>

// HACER esto:
{isOpen && (
  <div className="visible">
    <button>Click</button>
  </div>
)}
```

---

## IMPLEMENTACIÓN EN EL PROYECTO

### Archivos probables a modificar (frontend):

1. **Modal de Asignación Masiva**
   - Archivo: `AsignacionMasivaModal.tsx` o similar
   - Ubicación: `frontend/src/components/proveedores/`

2. **Dialogs/Modals genéricos**
   - Archivo: `Dialog.tsx`, `Modal.tsx`
   - Ubicación: `frontend/src/components/ui/`

### Patrón a buscar:
```bash
# En el frontend, buscar:
grep -r "aria-hidden" src/components/

# Buscar específicamente:
grep -r "aria-hidden.*true" src/components/ --include="*.tsx" --include="*.jsx"
```

---

## CÓDIGO EJEMPLO PROFESIONAL

### Modal Component (React + TypeScript)

```typescript
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, children }) => {
  if (!isOpen) return null; // Conditional rendering (mejor opción)

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"  // Usar aria-modal en lugar de aria-hidden
    >
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          className="modal-close"
          onClick={onClose}
          aria-label="Cerrar modal"
        >
          ×
        </button>
        {children}
      </div>
    </div>
  );
};
```

---

## VERIFICACIÓN

### Después de aplicar los cambios:

1. **Abrir DevTools Console**
2. **Realizar operación que muestra modal**
3. **Verificar que NO aparezcan warnings de aria-hidden**

### Checklist:
- [ ] No usar `aria-hidden="true"` en contenedores con botones/inputs
- [ ] Usar conditional rendering cuando sea posible
- [ ] Si necesario, agregar `tabIndex={-1}` a elementos internos
- [ ] Usar `aria-modal="true"` en modals en lugar de aria-hidden
- [ ] Probar navegación con teclado (Tab, Enter, Esc)

---

## RECURSOS ADICIONALES

- [WAI-ARIA Best Practices](https://www.w3.org/WAI/ARIA/apg/)
- [MDN: aria-hidden](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Attributes/aria-hidden)
- [MDN: inert attribute](https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/inert)

---

## NOTA IMPORTANTE

Este es un problema **SOLO del frontend**. El backend no tiene relación con estas alertas.

Las alertas aparecen porque el código frontend está usando `aria-hidden` incorrectamente.

**Responsable de implementar:** Frontend Developer
**Prioridad:** Media
**Estimación:** 30 minutos - 1 hora

---

**Documento creado por:** Backend Team
**Fecha:** 2025-10-21
**Status:** Documentado - Pendiente implementación en frontend
