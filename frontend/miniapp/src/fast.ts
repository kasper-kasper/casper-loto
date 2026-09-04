export function isFastLottery(code: string): boolean {
  return code === "flash" || code === "shadow" || code === "pulse";
}

export function splitPulseNumbers(values: number[]): { main: number[]; pulse: number[] } {
  return {
    main: values.filter((value) => value <= 10),
    pulse: values.filter((value) => value > 10).map((value) => value - 10),
  };
}
