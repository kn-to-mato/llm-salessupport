import { useState, useCallback } from 'react';
import { Copy, Check, FileText, Train, Hotel, Wallet, MapPin, Calendar, Target } from 'lucide-react';
import clsx from 'clsx';
import type { ApplicationPayload } from '../../types';

interface ApplicationDataCardProps {
  data: ApplicationPayload;
}

function DataRow({ icon: Icon, label, value, highlight = false }: {
  icon: typeof FileText;
  label: string;
  value: string | number;
  highlight?: boolean;
}) {
  const displayValue = typeof value === 'number' ? `¥${value.toLocaleString()}` : value;
  
  return (
    <div className="flex items-start gap-3 py-2">
      <Icon className={clsx("w-4 h-4 mt-0.5", highlight ? "text-accent-400" : "text-primary-400")} />
      <div className="flex-1">
        <div className="text-xs text-dark-400">{label}</div>
        <div className={clsx("text-sm", highlight ? "text-accent-400 font-bold text-lg" : "text-dark-100")}>
          {displayValue}
        </div>
      </div>
    </div>
  );
}

export function ApplicationDataCard({ data }: ApplicationDataCardProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    const text = JSON.stringify(data, null, 2);
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [data]);

  return (
    <div className="bg-dark-800/50 border border-primary-500/30 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-primary-500/10 border-b border-primary-500/20">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-primary-400" />
          <span className="font-medium text-primary-300">出張申請データ</span>
        </div>
        <button
          onClick={handleCopy}
          className={clsx(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-all",
            copied
              ? "bg-emerald-500/20 text-emerald-400"
              : "bg-dark-700 text-dark-300 hover:bg-dark-600 hover:text-dark-100"
          )}
        >
          {copied ? (
            <>
              <Check className="w-4 h-4" />
              コピー済み
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              JSONをコピー
            </>
          )}
        </button>
      </div>

      {/* Content */}
      <div className="p-4 space-y-1">
        <DataRow icon={MapPin} label="目的地" value={data.destination} />
        <DataRow icon={Calendar} label="期間" value={`${data.depart_date} 〜 ${data.return_date}`} />
        <DataRow icon={Target} label="目的" value={data.purpose} />
        
        <div className="border-t border-dark-700 my-2" />
        
        <DataRow icon={Train} label="交通手段" value={data.transportation} />
        <DataRow icon={Train} label="交通費" value={data.transportation_cost} />
        
        <div className="border-t border-dark-700 my-2" />
        
        <DataRow icon={Hotel} label="宿泊先" value={data.hotel} />
        <DataRow icon={Hotel} label="宿泊費" value={data.hotel_cost} />
        
        <div className="border-t border-dark-700 my-2" />
        
        <DataRow icon={Wallet} label="合計予算" value={data.total_budget} highlight />

        {data.notes && (
          <>
            <div className="border-t border-dark-700 my-2" />
            <div className="text-xs text-dark-400 bg-dark-900/50 rounded-lg p-3">
              📝 {data.notes}
            </div>
          </>
        )}
      </div>

      {/* JSON Preview */}
      <details className="group">
        <summary className="px-4 py-2 text-xs text-dark-500 cursor-pointer hover:text-dark-400 border-t border-dark-700">
          JSON形式で表示
        </summary>
        <pre className="px-4 py-3 text-xs font-mono text-dark-400 bg-dark-950 overflow-x-auto">
          {JSON.stringify(data, null, 2)}
        </pre>
      </details>
    </div>
  );
}

