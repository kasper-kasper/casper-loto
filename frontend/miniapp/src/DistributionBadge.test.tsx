import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { DistributionBadge } from "./DistributionBadge";

test("only the designated current draw shows the marker",()=>{
  const {rerender}=render(<DistributionBadge active={false}/>);
  expect(screen.queryByText("Распределительный")).not.toBeInTheDocument();
  rerender(<DistributionBadge active/>);
  expect(screen.getByText("Распределительный")).toBeInTheDocument();
  rerender(<DistributionBadge/>);
  expect(screen.queryByText("Распределительный")).not.toBeInTheDocument();
});
