"""Pydantic request models. Structural validation happens here (types,
sizes); semantic validation (unknown states, nondeterminism, ...) happens
in engine/automaton_io.py and is reported with a field path."""

from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

Str = Field(max_length=200)


class Transition(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    from_: str = Field(alias="from", max_length=200)
    symbol: str = Field(max_length=64)
    to: str = Field(max_length=200)


class Automaton(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: Literal["DFA", "NFA", "dfa", "nfa"]
    name: Optional[str] = Field(default=None, max_length=200)
    states: list[str] = Field(max_length=200)
    alphabet: list[str] = Field(max_length=64)
    start: str = Field(max_length=200)
    accept: list[str] = Field(max_length=200)
    transitions: list[Transition] = Field(max_length=5000)
    descriptions: Optional[dict[str, str]] = None

    def spec(self) -> dict:
        d = self.model_dump(by_alias=True, exclude_none=True)
        d["type"] = d["type"].upper()
        return d


InputValue = Union[str, list[str]]


class RunRequest(BaseModel):
    automaton: Automaton
    input: InputValue = Field(default="")
    save: bool = False


class AutomatonOnly(BaseModel):
    automaton: Automaton
    save: bool = False


class SubsetRequest(AutomatonOnly):
    include_dead_state: bool = True


class PairRequest(BaseModel):
    a: Automaton
    b: Automaton
    save: bool = False


class BoundedRequest(PairRequest):
    max_length: int = Field(default=6, ge=0, le=12)
    random_count: int = Field(default=200, ge=0, le=5000)
    random_max_length: int = Field(default=40, ge=1, le=500)
    seed: int = Field(default=7, ge=0, le=2**31)


class CompareRequest(PairRequest):
    input: Optional[InputValue] = None


class MotifInput(BaseModel):
    name: Optional[str] = Field(default=None, max_length=60)
    pattern: str = Field(min_length=1, max_length=200)


class RnaAnalyzeRequest(BaseModel):
    text: str = Field(max_length=2_000_000)
    convert_t: bool = True
    record_index: int = Field(default=0, ge=0, le=10000)
    min_orf_codons: int = Field(default=0, ge=0, le=10000)
    motifs: list[MotifInput] = Field(default_factory=list, max_length=5)
    filename: Optional[str] = Field(default=None, max_length=200)
    save: bool = False


class OrfTraceRequest(BaseModel):
    sequence: str = Field(max_length=200_000)
    frame: int = Field(ge=0, le=2)


class MotifCompileRequest(BaseModel):
    pattern: str = Field(min_length=1, max_length=200)


class FoldRequest(BaseModel):
    sequence: str = Field(max_length=10_000)
    min_loop: int = Field(default=3, ge=0, le=10)
    save: bool = False


class HairpinRequest(BaseModel):
    sequence: str = Field(max_length=10_000)
    min_len: int = Field(default=4, ge=2, le=16)
    max_len: int = Field(default=10, ge=2, le=16)
    allow_center: bool = False
