#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/src/apex/grpc/generated"
mkdir -p "$OUT"
python -m grpc_tools.protoc \
  -I "$ROOT/protos" \
  --python_out="$OUT" \
  --grpc_python_out="$OUT" \
  "$ROOT/protos/arb.proto"
touch "$OUT/__init__.py"
# Fix relative imports in generated grpc module
if [[ -f "$OUT/arb_pb2_grpc.py" ]]; then
  sed -i 's/import arb_pb2/from apex.grpc.generated import arb_pb2/' "$OUT/arb_pb2_grpc.py" 2>/dev/null || \
  sed -i '' 's/import arb_pb2/from apex.grpc.generated import arb_pb2/' "$OUT/arb_pb2_grpc.py" 2>/dev/null || true
fi
echo "Generated gRPC stubs in $OUT"
