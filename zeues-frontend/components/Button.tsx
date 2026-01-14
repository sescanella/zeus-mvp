import { ButtonHTMLAttributes } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'iniciar' | 'completar' | 'cancelar' | 'cancel';
}

export function Button({
  children,
  variant = 'primary',
  disabled,
  className = '',
  ...props
}: ButtonProps) {
  const variants = {
    primary: 'bg-zeues-orange hover:bg-zeues-orange-dark text-white',
    iniciar: 'bg-zeues-cyan hover:bg-zeues-blue text-white',
    completar: 'bg-zeues-green hover:bg-green-700 text-white',
    cancelar: 'bg-zeues-warning hover:bg-zeues-red text-white',  // v2.0: CANCELAR acción EN_PROGRESO
    cancel: 'bg-gray-400 hover:bg-gray-500 text-white',  // Abandonar flujo completo
  };

  return (
    <button
      {...props}
      disabled={disabled}
      className={`
        w-full h-16 rounded-lg text-xl font-semibold
        transition-colors duration-200
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variants[variant]}
        ${className}
      `}
    >
      {children}
    </button>
  );
}
