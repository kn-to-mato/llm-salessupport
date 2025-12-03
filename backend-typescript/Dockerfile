FROM node:20-alpine AS builder

WORKDIR /app

# パッケージファイルをコピー
COPY package*.json ./

# 依存関係をインストール
RUN npm ci

# ソースコードをコピー
COPY . .

# ビルド
RUN npm run build

# 本番用イメージ
FROM node:20-alpine AS runner

WORKDIR /app

# 本番用依存関係のみインストール
COPY package*.json ./
RUN npm ci --only=production

# ビルド成果物をコピー
COPY --from=builder /app/dist ./dist

# 環境変数
ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

CMD ["node", "dist/index.js"]

