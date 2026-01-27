// zeues-frontend/components/ConnectionStatus.tsx
// Visual indicator for SSE connection status

interface ConnectionStatusProps {
  connected: boolean;
}

export function ConnectionStatus({ connected }: ConnectionStatusProps) {
  return (
    <div className="fixed top-6 right-6 z-50 flex items-center gap-2 bg-[#001F3F] px-3 py-2 border-2 border-white">
      <div
        className={`w-3 h-3 rounded-full ${
          connected ? 'bg-green-500' : 'bg-red-500'
        }`}
      />
      <span className="text-xs font-black font-mono text-white">
        {connected ? 'CONECTADO' : 'DESCONECTADO'}
      </span>
    </div>
  );
}
