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
    primary: 'bg-[#FF5B00] hover:bg-[#E64A19] text-white',
    iniciar: 'bg-cyan-600 hover:bg-cyan-700 text-white',
    completar: 'bg-green-600 hover:bg-green-700 text-white',
    cancelar: 'bg-yellow-600 hover:bg-yellow-700 text-white',  // v2.0: CANCELAR acción EN_PROGRESO
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
