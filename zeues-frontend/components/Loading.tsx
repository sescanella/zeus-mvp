interface LoadingProps {
  message?: string;
}

export function Loading({ message = 'CARGANDO' }: LoadingProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      {/* Border progresivo OPTIMIZADO - cuadrado que se dibuja */}
      <div className="relative w-48 h-48 mb-8">
        {/* Top border - izquierda a derecha */}
        <div className="border-top will-change-transform"></div>

        {/* Right border - arriba a abajo */}
        <div className="border-right will-change-transform"></div>

        {/* Bottom border - derecha a izquierda */}
        <div className="border-bottom will-change-transform"></div>

        {/* Left border - abajo a arriba */}
        <div className="border-left will-change-transform"></div>

        {/* Centro - indicador naranja pulsante */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="center-pulse will-change-transform"></div>
        </div>
      </div>

      {/* Texto con puntos animados */}
      <div className="flex items-center gap-1">
        <h2 className="text-2xl font-black text-slate-700 tracking-[0.25em] font-mono">
          {message}
        </h2>
        <div className="flex gap-0 items-end h-8">
          <span className="dot-1">.</span>
          <span className="dot-2">.</span>
          <span className="dot-3">.</span>
        </div>
      </div>

      <style jsx>{`
        /* Border animations - GPU optimized with transform */
        .border-top {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 4px;
          background: #FF5B00;
          transform-origin: left;
          animation: drawTop 3s ease-in-out infinite;
        }

        .border-right {
          position: absolute;
          top: 0;
          right: 0;
          width: 4px;
          height: 100%;
          background: #FF5B00;
          transform-origin: top;
          animation: drawRight 3s ease-in-out infinite;
        }

        .border-bottom {
          position: absolute;
          bottom: 0;
          right: 0;
          width: 100%;
          height: 4px;
          background: #FF5B00;
          transform-origin: right;
          animation: drawBottom 3s ease-in-out infinite;
        }

        .border-left {
          position: absolute;
          bottom: 0;
          left: 0;
          width: 4px;
          height: 100%;
          background: #FF5B00;
          transform-origin: bottom;
          animation: drawLeft 3s ease-in-out infinite;
        }

        .center-pulse {
          width: 32px;
          height: 32px;
          background: #FF5B00;
          animation: centerPulse 3s ease-in-out infinite;
        }

        /* Dots animation */
        .dot-1,
        .dot-2,
        .dot-3 {
          font-size: 1.5rem;
          line-height: 2rem;
          font-weight: 900;
          color: #334155;
          font-family: ui-monospace, monospace;
          animation: dotPulse 1.5s ease-in-out infinite;
        }

        .dot-2 {
          animation-delay: 0.3s;
        }

        .dot-3 {
          animation-delay: 0.6s;
        }

        /* Keyframes - GPU accelerated */
        @keyframes drawTop {
          0% { transform: scaleX(0); }
          20% { transform: scaleX(1); }
          100% { transform: scaleX(1); }
        }

        @keyframes drawRight {
          0%, 20% { transform: scaleY(0); }
          40% { transform: scaleY(1); }
          100% { transform: scaleY(1); }
        }

        @keyframes drawBottom {
          0%, 40% { transform: scaleX(0); }
          60% { transform: scaleX(1); }
          100% { transform: scaleX(1); }
        }

        @keyframes drawLeft {
          0%, 60% { transform: scaleY(0); }
          80% { transform: scaleY(1); }
          100% { transform: scaleY(1); }
        }

        @keyframes centerPulse {
          0%, 80% { transform: scale(0.8); opacity: 0.6; }
          85%, 95% { transform: scale(1.2); opacity: 1; }
          100% { transform: scale(0.8); opacity: 0.6; }
        }

        @keyframes dotPulse {
          0%, 100% { opacity: 0.3; transform: translateY(0); }
          50% { opacity: 1; transform: translateY(-2px); }
        }
      `}</style>
    </div>
  );
}
