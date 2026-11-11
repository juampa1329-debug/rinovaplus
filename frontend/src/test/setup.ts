import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach } from "vitest";
import { mockLocalClients } from "./localClientsMock";

beforeEach(mockLocalClients);

afterEach(cleanup);
