import { MapPin, Train, Hotel, FileCheck, Sparkles } from 'lucide-react';

const features = [
  {
    icon: MapPin,
    title: '条件の整理',
    description: '出発地、目的地、日程などを整理します',
  },
  {
    icon: FileCheck,
    title: '規程チェック',
    description: '社内旅費規程に照らして確認します',
  },
  {
    icon: Train,
    title: '交通候補の検索',
    description: '新幹線・飛行機の候補を提示します',
  },
  {
    icon: Hotel,
    title: '宿泊候補の検索',
    description: 'ビジネスホテルの候補を提示します',
  },
];

const examples = [
  '来週、大阪に2泊3日で出張したいです。東京発で、予算は6万円以内。',
  '12月10日から福岡に出張予定です。できれば飛行機で。',
  '名古屋に日帰りで行きたいのですが、新幹線で行けますか？',
];

interface WelcomeMessageProps {
  onExampleClick: (example: string) => void;
}

export function WelcomeMessage({ onExampleClick }: WelcomeMessageProps) {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-2xl text-center animate-fade-in">
        {/* Icon */}
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500/20 to-accent-500/20 border border-primary-500/30 mb-6 glow-primary">
          <Sparkles className="w-8 h-8 text-primary-400" />
        </div>

        {/* Title */}
        <h2 className="text-2xl font-bold mb-2 gradient-text">
          出張計画をサポートします
        </h2>
        <p className="text-dark-400 mb-8">
          出張の希望を自然文で入力してください。AIが最適なプランを提案します。
        </p>

        {/* Features */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="p-4 rounded-xl bg-dark-900/50 border border-dark-700/50"
            >
              <feature.icon className="w-6 h-6 text-primary-400 mx-auto mb-2" />
              <div className="text-sm font-medium text-dark-200">{feature.title}</div>
              <div className="text-xs text-dark-500 mt-1">{feature.description}</div>
            </div>
          ))}
        </div>

        {/* Examples */}
        <div className="text-left">
          <div className="text-xs text-dark-500 mb-3 uppercase tracking-wide">
            入力例
          </div>
          <div className="space-y-2">
            {examples.map((example) => (
              <button
                key={example}
                onClick={() => onExampleClick(example)}
                className="w-full text-left px-4 py-3 rounded-xl bg-dark-800/50 border border-dark-700/50 text-sm text-dark-300 hover:bg-dark-800 hover:border-primary-500/30 hover:text-dark-100 transition-all duration-200"
              >
                "{example}"
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
