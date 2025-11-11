interface LoadingProps {
  message?: string;
}

export function Loading({ message = 'Cargando...' }: LoadingProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="animate-spin w-12 h-12 border-4 border-cyan-600
                      border-t-transparent rounded-full mb-4">
      </div>
      <p className="text-lg text-gray-600">{message}</p>
    </div>
  );
}
