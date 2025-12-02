import { Train, Plane, Hotel, Calendar, Wallet, CheckCircle, AlertCircle, XCircle } from 'lucide-react';
import clsx from 'clsx';
import type { TravelPlan } from '../../types';

interface PlanCardProps {
  plan: TravelPlan;
  onSelect: () => void;
}

function PolicyBadge({ status }: { status: TravelPlan['summary']['policy_status'] }) {
  const config = {
    OK: {
      icon: CheckCircle,
      text: '規程OK',
      className: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    },
    NG: {
      icon: XCircle,
      text: '規程NG',
      className: 'bg-red-500/20 text-red-400 border-red-500/30',
    },
    '注意': {
      icon: AlertCircle,
      text: '要確認',
      className: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    },
  }[status];

  const Icon = config.icon;

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border",
        config.className
      )}
    >
      <Icon className="w-3.5 h-3.5" />
      {config.text}
    </span>
  );
}

function TransportIcon({ type }: { type: string }) {
  if (type.includes('飛行機') || type.includes('航空')) {
    return <Plane className="w-4 h-4" />;
  }
  return <Train className="w-4 h-4" />;
}

export function PlanCard({ plan, onSelect }: PlanCardProps) {
  const { summary, outbound_transportation, hotel } = plan;

  return (
    <div
      className={clsx(
        "bg-dark-800/50 border border-dark-700/50 rounded-xl p-4",
        "hover:border-primary-500/50 hover:bg-dark-800/80",
        "transition-all duration-200 group"
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-white">{plan.label}</h3>
        <PolicyBadge status={summary.policy_status} />
      </div>

      {/* Date */}
      <div className="flex items-center gap-2 text-sm text-dark-300 mb-3">
        <Calendar className="w-4 h-4 text-primary-400" />
        <span>{summary.depart_date} 〜 {summary.return_date}</span>
      </div>

      {/* Transportation */}
      {outbound_transportation && (
        <div className="flex items-start gap-2 text-sm mb-3">
          <div className="text-primary-400 mt-0.5">
            <TransportIcon type={outbound_transportation.type} />
          </div>
          <div>
            <div className="text-dark-200">
              {outbound_transportation.departure_station} → {outbound_transportation.arrival_station}
            </div>
            <div className="text-dark-400 text-xs">
              {outbound_transportation.train_name} {outbound_transportation.departure_time}発
              {' ・ '}
              ¥{outbound_transportation.price.toLocaleString()}(片道)
            </div>
          </div>
        </div>
      )}

      {/* Hotel */}
      {hotel && (
        <div className="flex items-start gap-2 text-sm mb-3">
          <Hotel className="w-4 h-4 text-primary-400 mt-0.5" />
          <div>
            <div className="text-dark-200">{hotel.name}</div>
            <div className="text-dark-400 text-xs">
              {hotel.area} ・ ¥{hotel.price_per_night.toLocaleString()}/泊 × {hotel.nights}泊
              {hotel.rating && (
                <span className="ml-2">★ {hotel.rating}</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Policy Note */}
      {summary.policy_note && (
        <div className="text-xs text-amber-400/80 bg-amber-500/10 rounded-lg px-3 py-2 mb-3">
          ⚠️ {summary.policy_note}
        </div>
      )}

      {/* Total */}
      <div className="flex items-center justify-between pt-3 border-t border-dark-700">
        <div className="flex items-center gap-2 text-sm text-dark-300">
          <Wallet className="w-4 h-4 text-accent-400" />
          <span>概算総額</span>
        </div>
        <div className="text-xl font-bold text-accent-400">
          ¥{summary.estimated_total.toLocaleString()}
        </div>
      </div>

      {/* Action Button */}
      <button
        onClick={onSelect}
        className={clsx(
          "w-full mt-4 py-3 px-4 rounded-xl font-medium text-sm",
          "bg-gradient-to-r from-primary-500 to-primary-600",
          "hover:from-primary-400 hover:to-primary-500",
          "transition-all duration-200",
          "focus:outline-none focus:ring-2 focus:ring-primary-400 focus:ring-offset-2 focus:ring-offset-dark-800"
        )}
      >
        このプランで申請案を作成
      </button>
    </div>
  );
}
