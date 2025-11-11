interface ListItem {
  id: string;
  label: string;
  subtitle?: string;
}

interface ListProps {
  items: ListItem[];
  onItemClick: (id: string) => void;
  emptyMessage?: string;
}

export function List({ items, onItemClick, emptyMessage = 'No hay items' }: ListProps) {
  if (items.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <button
          key={item.id}
          onClick={() => onItemClick(item.id)}
          className="w-full p-4 bg-white rounded-lg shadow hover:shadow-md
                     transition-shadow text-left border border-gray-200"
        >
          <p className="text-lg font-semibold text-slate-900">{item.label}</p>
          {item.subtitle && (
            <p className="text-sm text-gray-600 mt-1">{item.subtitle}</p>
          )}
        </button>
      ))}
    </div>
  );
}
