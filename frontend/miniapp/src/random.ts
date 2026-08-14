function secureIndex(maxExclusive: number): number {
  const range = 0x1_0000_0000;
  const limit = range - (range % maxExclusive);
  const value = new Uint32Array(1);
  do {
    crypto.getRandomValues(value);
  } while (value[0] >= limit);
  return value[0] % maxExclusive;
}

export function randomCombination(maxNumber: number, count: number): number[] {
  const available = Array.from({ length: maxNumber }, (_, index) => index + 1);
  for (let index = available.length - 1; index > 0; index -= 1) {
    const target = secureIndex(index + 1);
    [available[index], available[target]] = [available[target], available[index]];
  }
  return available.slice(0, count).sort((left, right) => left - right);
}
