from __future__ import annotations
import logging
import time
from copy import deepcopy
from collections import deque
from dataclasses import dataclass, field
from typing import Any
import pulp
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s %(name)s — %(message)s")
    )
    logger.addHandler(_handler)
def _slot_day(slot_id: str) -> str:
    return slot_id.split("_", 1)[0] if "_" in slot_id else slot_id

def _slot_time(slot_id: str) -> str:
    return slot_id.split("_", 1)[1] if "_" in slot_id else slot_id

def _format_slot_range(slot_time: str, duration_minutes: int = 40) -> str:
    from datetime import datetime, timedelta
    start = datetime.strptime(slot_time, "%H:%M")
    end = start + timedelta(minutes=duration_minutes)
    return f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}"

@dataclass
class Teacher:
    teacher_id: str
    name: str
    max_hours: int                          
    available_slots: list[str]              
    subject_expertise: list[str]            
    preferred_slots: list[str] = field(default_factory=list)

@dataclass
class Room:
    room_id: str
    name: str
    capacity: int
    room_type: str                           
    available_slots: list[str]               
@dataclass
class Subject:
    subject_id: str
    name: str
    required_hours: int                      
    department: str
    required_room_type: str                  
    eligible_teachers: list[str]             
    batch_ids: list[str]                     
    min_batch_size: int = 0                  
@dataclass
class Batch:
    batch_id: str
    name: str
    size: int
    semester: int
    branch: str
@dataclass
class SchedulingInput:
    teachers: dict[str, Teacher]
    rooms: dict[str, Room]
    subjects: dict[str, Subject]
    batches: dict[str, Batch]
    time_slots: list[str]
    break_slots: list[str] = field(default_factory=list)
    risk_scores: dict[tuple[str, str, str, str], float] = field(default_factory=dict)
    preference_scores: dict[tuple[str, str], float] = field(default_factory=dict)

@dataclass
class Assignment:
    teacher_id: str
    teacher_name: str
    room_id: str
    room_name: str
    slot_id: str
    subject_id: str
    subject_name: str
    batch_ids: list[str]
    risk_score: float = 0.0
@dataclass
class TimetableVariant:
    variant_index: int
    assignments: list[Assignment]
    objective_score: float
    feasible: bool
    weights_used: dict[str, float]
    solve_time_seconds: float
    explanation: str = ""
_WEIGHT_PROFILES: list[dict[str, float]] = [
    {"w_satisfaction": 3.0, "w_utilization": 2.0, "w_preference": 2.0,
     "w_risk": 5.0, "w_fragmentation": 1.0},
    {"w_satisfaction": 2.0, "w_utilization": 5.0, "w_preference": 1.0,
     "w_risk": 4.0, "w_fragmentation": 1.5},
    {"w_satisfaction": 2.0, "w_utilization": 1.5, "w_preference": 5.0,
     "w_risk": 4.0, "w_fragmentation": 1.0},
    {"w_satisfaction": 1.5, "w_utilization": 1.5, "w_preference": 1.5,
     "w_risk": 8.0, "w_fragmentation": 1.0},
    {"w_satisfaction": 2.0, "w_utilization": 2.0, "w_preference": 2.0,
     "w_risk": 4.0, "w_fragmentation": 4.0},
]
_NUM_VARIANTS = len(_WEIGHT_PROFILES)  
def gale_shapley_matching(
    teachers: dict[str, Teacher],
    subjects: dict[str, Subject],
    batches: dict[str, Batch],
) -> dict[tuple[str, str], str]:
    tasks: list[tuple[str, str]] = [
        (batch_id, subject_id)
        for subject_id, subject in subjects.items()
        for batch_id in subject.batch_ids
    ]
    if not tasks:
        return {}
    teacher_caps: dict[str, int] = {
        teacher_id: max(1, teacher.max_hours)
        for teacher_id, teacher in teachers.items()
    }
    task_prefs: dict[tuple[str, str], list[str]] = {}
    teacher_ranks: dict[str, dict[tuple[str, str], tuple[int, int, int]]] = {}
    for teacher_id, teacher in teachers.items():
        expertise_rank = {subject_id: idx for idx, subject_id in enumerate(teacher.subject_expertise)}
        teacher_ranks[teacher_id] = {}
        for batch_id, subject_id in tasks:
            subject = subjects[subject_id]
            if subject_id not in expertise_rank:
                continue
            teacher_ranks[teacher_id][(batch_id, subject_id)] = (
                expertise_rank[subject_id],
                -subject.required_hours,
                -batches[batch_id].size,
            )
    for batch_id, subject_id in tasks:
        subject = subjects[subject_id]
        prefs = [
            teacher_id
            for teacher_id in subject.eligible_teachers
            if teacher_id in teachers and (batch_id, subject_id) in teacher_ranks.get(teacher_id, {})
        ]
        if not prefs:
            prefs = [
                teacher_id
                for teacher_id, teacher in teachers.items()
                if subject_id in teacher.subject_expertise
            ]
        task_prefs[(batch_id, subject_id)] = prefs
    next_choice: dict[tuple[str, str], int] = {task: 0 for task in tasks}
    accepted: dict[str, list[tuple[str, str]]] = {teacher_id: [] for teacher_id in teachers}
    load_hours: dict[str, int] = {teacher_id: 0 for teacher_id in teachers}
    match: dict[tuple[str, str], str] = {}
    queue: deque[tuple[str, str]] = deque(tasks)
    while queue:
        task = queue.popleft()
        prefs = task_prefs.get(task, [])
        if not prefs:
            continue
        if next_choice[task] >= len(prefs):
            fallback = [
                teacher_id
                for teacher_id in teachers
                if task in teacher_ranks.get(teacher_id, {})
                and teacher_id not in prefs
            ]
            prefs = prefs + fallback
            task_prefs[task] = prefs
        if next_choice[task] >= len(prefs):
            continue
        teacher_id = prefs[next_choice[task]]
        next_choice[task] += 1
        if task not in teacher_ranks.get(teacher_id, {}):
            queue.append(task)
            continue
        accepted[teacher_id].append(task)
        match[task] = teacher_id
        load_hours[teacher_id] += subjects[task[1]].required_hours
        while load_hours[teacher_id] > teacher_caps[teacher_id] and accepted[teacher_id]:
            worst_task = max(accepted[teacher_id], key=lambda tk: teacher_ranks[teacher_id][tk])
            accepted[teacher_id].remove(worst_task)
            load_hours[teacher_id] -= subjects[worst_task[1]].required_hours
            if worst_task in match:
                del match[worst_task]
            if worst_task != task:
                queue.append(worst_task)
                break
            queue.append(task)
            break
    for task in tasks:
        if task not in match:
            subject_id = task[1]
            fallback_teachers = [
                teacher_id
                for teacher_id, teacher in teachers.items()
                if subject_id in teacher.subject_expertise
            ]
            if not fallback_teachers:
                raise ValueError(f"No teacher can teach subject {subject_id}")
            match[task] = fallback_teachers[0]
    return match
def _validate_input(data: SchedulingInput) -> None:
    if not data.teachers:
        raise ValueError("SchedulingInput.teachers is empty — nothing to schedule.")
    if not data.rooms:
        raise ValueError("SchedulingInput.rooms is empty — no rooms available.")
    if not data.subjects:
        raise ValueError("SchedulingInput.subjects is empty — no subjects to assign.")
    if not data.batches:
        raise ValueError("SchedulingInput.batches is empty — no student batches.")
    if not data.time_slots:
        raise ValueError("SchedulingInput.time_slots is empty — no slots defined.")
    all_teacher_ids = set(data.teachers)
    all_room_ids = set(data.rooms)
    all_batch_ids = set(data.batches)
    all_slot_ids = set(data.time_slots)
    if data.break_slots:
        invalid_breaks = set(data.break_slots) - all_slot_ids
        if invalid_breaks:
            raise ValueError(f"SchedulingInput.break_slots references unknown slots: {invalid_breaks}.")
    for subj in data.subjects.values():
        if subj.required_hours <= 0:
            raise ValueError(
                f"Subject '{subj.subject_id}' has required_hours={subj.required_hours}."
                " Must be a positive integer."
            )
        for tid in subj.eligible_teachers:
            if tid not in all_teacher_ids:
                raise ValueError(
                    f"Subject '{subj.subject_id}' references unknown teacher '{tid}'."
                )
        for bid in subj.batch_ids:
            if bid not in all_batch_ids:
                raise ValueError(
                    f"Subject '{subj.subject_id}' references unknown batch '{bid}'."
                )
    for teacher in data.teachers.values():
        if teacher.max_hours <= 0:
            raise ValueError(
                f"Teacher '{teacher.teacher_id}' has max_hours={teacher.max_hours}."
                " Must be positive."
            )
        invalid_slots = set(teacher.available_slots) - all_slot_ids
        if invalid_slots:
            raise ValueError(
                f"Teacher '{teacher.teacher_id}' references unknown slots: {invalid_slots}."
            )
    for room in data.rooms.values():
        if room.capacity <= 0:
            raise ValueError(
                f"Room '{room.room_id}' has capacity={room.capacity}. Must be positive."
            )
        invalid_slots = set(room.available_slots) - all_slot_ids
        if invalid_slots:
            raise ValueError(
                f"Room '{room.room_id}' references unknown slots: {invalid_slots}."
            )
    for key, score in data.risk_scores.items():
        if len(key) == 4:
            t, r, s, c = key
        elif len(key) == 5:
            t, r, s, c, b = key
        else:
            raise ValueError(f"Invalid risk key format: {key}")
        if not (0.0 <= score <= 1.0):
            raise ValueError(
                f"risk_scores[{key}] = {score} is outside [0, 1]."
            )
    logger.info("Input validation passed: %d teachers, %d rooms, %d subjects, "
                "%d batches, %d slots.",
                len(data.teachers), len(data.rooms), len(data.subjects),
                len(data.batches), len(data.time_slots))
class TimetableOptimizer:
    SOLVER_TIME_LIMIT: int = 8
    def __init__(self, data: SchedulingInput) -> None:
        _validate_input(data)
        self._data = data
        self._break_slots = set(data.break_slots)
        self._task_teacher_map = gale_shapley_matching(data.teachers, data.subjects, data.batches)
        self._feasible_keys: list[tuple[str, str, str, str, str]] = self._compute_feasible_keys()
        for c_id, subj in data.subjects.items():
            for b_id in subj.batch_ids:
                if not any(key[3] == c_id and key[4] == b_id for key in self._feasible_keys):
                    raise ValueError(f"No feasible assignment keys for subject {c_id} and batch {b_id}")
        self._keys_by_teacher_slot: dict[tuple[str, str], list[tuple[str, str, str, str, str]]] = {}
        self._keys_by_room_slot: dict[tuple[str, str], list[tuple[str, str, str, str, str]]] = {}
        self._keys_by_subject: dict[str, list[tuple[str, str, str, str, str]]] = {}
        self._keys_by_batch_slot: dict[tuple[str, str], list[tuple[str, str, str, str, str]]] = {}
        self._keys_by_teacher: dict[str, list[tuple[str, str, str, str, str]]] = {}
        self._keys_by_batch_subject_day: dict[tuple[str, str, str], list[tuple[str, str, str, str, str]]] = {}
        for key in self._feasible_keys:
            t_id, r_id, s_id, c_id, b_id = key
            day = _slot_day(s_id)
            self._keys_by_teacher_slot.setdefault((t_id, s_id), []).append(key)
            self._keys_by_room_slot.setdefault((r_id, s_id), []).append(key)
            self._keys_by_subject.setdefault(c_id, []).append(key)
            self._keys_by_teacher.setdefault(t_id, []).append(key)
            self._keys_by_batch_slot.setdefault((b_id, s_id), []).append(key)
            self._keys_by_batch_subject_day.setdefault((b_id, c_id, day), []).append(key)
        logger.info("Feasible assignment keys: %d", len(self._feasible_keys))
        self._slot_index: dict[str, int] = {s: i for i, s in enumerate(data.time_slots)}
    def generate_variants(self) -> list[TimetableVariant]:
        logger.info("Starting variant generation (%d variants requested).", _NUM_VARIANTS)
        variants: list[TimetableVariant] = []
        previous_solutions: list[dict[tuple[str, str, str, str, str], int]] = []
        for idx, weight_profile in enumerate(_WEIGHT_PROFILES):
            logger.info("Solving variant %d/%d with weights: %s", idx + 1, _NUM_VARIANTS, weight_profile)
            prob, x_vars = self.build_model(weight_profile)
            self._add_no_good_cuts(prob, x_vars, previous_solutions)
            variant = self.solve(prob, x_vars, idx + 1, weight_profile)
            variants.append(variant)
            if variant.feasible:
                solution_snapshot = {
                    key: int(round(pulp.value(x_vars[key])))
                    for key in self._feasible_keys
                    if pulp.value(x_vars[key]) is not None and pulp.value(x_vars[key]) > 0.5
                }
                previous_solutions.append(solution_snapshot)
                logger.info(
                    "Variant %d feasible — score=%.4f, assignments=%d.",
                    idx + 1,
                    variant.objective_score,
                    len(variant.assignments),
                )
            else:
                logger.warning("Variant %d is infeasible or timed out.", idx + 1)
        feasible_count = sum(1 for v in variants if v.feasible)
        if feasible_count < 1:
            raise RuntimeError(
                f"Only {feasible_count} feasible variant(s) found out of {_NUM_VARIANTS} attempts. "
                "The problem may be over constrained...Review teacher availability...room counts, and subject hours."
            )
        variants.sort(key=lambda v: v.objective_score, reverse=True)
        logger.info("Variant generation complete.  %d/%d feasible.", feasible_count, _NUM_VARIANTS)
        return variants

    def build_model(
        self,
        weights: dict[str, float],
    ) -> tuple[pulp.LpProblem, dict[tuple[str, str, str, str, str], pulp.LpVariable]]:

        prob = pulp.LpProblem("Time_Table", pulp.LpMaximize)
        x: dict[tuple[str, str, str, str, str], pulp.LpVariable] = {}
        for key in self._feasible_keys:
            t_id, r_id, s_id, c_id, b_id = key
            x[key] = pulp.LpVariable(f"x_{t_id}__{r_id}__{s_id}__{c_id}__{b_id}", cat=pulp.const.LpBinary)
        self._add_teacher_clash_constraints(prob, x)
        self._add_room_clash_constraints(prob, x)
        self._add_curriculum_fulfillment_constraints(prob, x)
        self._add_teacher_workload_constraints(prob, x)
        self._add_batch_conflict_constraints(prob, x)
        self._add_batch_subject_day_constraints(prob, x)
        self._add_risk_hard_blocks(prob, x)
        self._add_fragmentation_constraints(prob, x)
        prob += self._build_objective(x, weights), "Weighted_Objective"
        return prob, x
    def solve(
        self,
        prob: pulp.LpProblem,
        x_vars: dict[tuple[str, str, str, str, str], pulp.LpVariable],
        variant_index: int,
        weights: dict[str, float],
    ) -> TimetableVariant:
        solver = pulp.getSolver(
            "PULP_CBC_CMD",
            timeLimit=self.SOLVER_TIME_LIMIT,
            msg=0,
            gapRel=0.02,
            threads=4,
        )
        start = time.perf_counter()
        prob.solve(solver)
        elapsed = time.perf_counter() - start
        status = pulp.LpStatus[prob.status]
        obj_value = float(pulp.value(prob.objective) or 0.0)
        logger.debug(
            "Variant %d CBC status=%s  objective=%.4f  time=%.2fs",
            variant_index,
            status,
            obj_value,
            elapsed,
        )
        feasible = status == "Optimal" or (status == "Not Solved" and self._has_valid_solution(x_vars))
        assignments: list[Assignment] = []
        if feasible:
            assignments = self.extract_solution(x_vars)
        explanation = self._build_explanation(variant_index, status, obj_value, assignments, weights)
        return TimetableVariant(
            variant_index=variant_index,
            assignments=assignments,
            objective_score=round(obj_value, 4),
            feasible=feasible,
            weights_used=deepcopy(weights),
            solve_time_seconds=round(elapsed, 3),
            explanation=explanation,
        )
    def extract_solution(
        self,
        x_vars: dict[tuple[str, str, str, str, str], pulp.LpVariable],
    ) -> list[Assignment]:
        data = self._data
        assignments: list[Assignment] = []
        for (t_id, r_id, s_id, c_id, b_id), var in x_vars.items():
            val = pulp.value(var)
            if val is None or val < 0.5:
                continue
            teacher = data.teachers[t_id]
            room = data.rooms[r_id]
            subject = data.subjects[c_id]
            risk = data.risk_scores.get((t_id, r_id, s_id, c_id, b_id))
            if risk is None:
                risk = data.risk_scores.get((t_id, r_id, s_id, c_id), 0.0)
            assignments.append(
                Assignment(
                    teacher_id=t_id,
                    teacher_name=teacher.name,
                    room_id=r_id,
                    room_name=room.name,
                    slot_id=s_id,
                    subject_id=c_id,
                    subject_name=subject.name,
                    batch_ids=[b_id],
                    risk_score=risk,
                )
            )
        assignments.sort(key=lambda a: (a.slot_id, a.room_id, a.subject_id, a.teacher_id))
        return assignments
    def _has_valid_solution(self, x_vars: dict[tuple[str, str, str, str, str], pulp.LpVariable]) -> bool:
        data = self._data
        for key in self._feasible_keys:
            val = pulp.value(x_vars[key])
            if val is None:
                return False
        for c_id, subj in data.subjects.items():
            for b_id in subj.batch_ids:
                assigned = sum(
                    1
                    for key in self._feasible_keys
                    if key[3] == c_id
                    and key[4] == b_id
                    and pulp.value(x_vars[key]) is not None
                    and pulp.value(x_vars[key]) > 0.5
                )
                if assigned != subj.required_hours:
                    return False
        for t_id in data.teachers:
            for s_id in data.time_slots:
                assigned = sum(
                    1
                    for key in self._keys_by_teacher_slot.get((t_id, s_id), [])
                    if pulp.value(x_vars[key]) is not None and pulp.value(x_vars[key]) > 0.5
                )
                if assigned > 1:
                    return False
            total = sum(
                1
                for key in self._keys_by_teacher.get(t_id, [])
                if pulp.value(x_vars[key]) is not None and pulp.value(x_vars[key]) > 0.5
            )
            if total > data.teachers[t_id].max_hours:
                return False
        for r_id in data.rooms:
            for s_id in data.time_slots:
                assigned = sum(
                    1
                    for key in self._keys_by_room_slot.get((r_id, s_id), [])
                    if pulp.value(x_vars[key]) is not None and pulp.value(x_vars[key]) > 0.5
                )
                if assigned > 1:
                    return False
        for b_id in data.batches:
            for s_id in data.time_slots:
                assigned = sum(
                    1
                    for key in self._keys_by_batch_slot.get((b_id, s_id), [])
                    if pulp.value(x_vars[key]) is not None and pulp.value(x_vars[key]) > 0.5
                )
                if assigned > 1:
                    return False
        for key in self._feasible_keys:
            val = pulp.value(x_vars[key])
            if val is not None and val > 0.5:
                risk = self._data.risk_scores.get(key)
                if risk is None:
                    t_id, r_id, s_id, c_id, b_id = key
                    risk = self._data.risk_scores.get((t_id, r_id, s_id, c_id), 0.0)
                if risk >= 1.0:
                    return False
        return True
    def _add_fragmentation_constraints(
        self,
        prob: pulp.LpProblem,
        x: dict[tuple[str, str, str, str, str], pulp.LpVariable],
    ) -> None:
        self._fragmentation_gap_vars: dict[tuple[str, str], pulp.LpVariable] = {}
        slot_day_groups: dict[str, list[str]] = {}
        for slot_id in self._data.time_slots:
            day = slot_id.split("_")[0]
            slot_day_groups.setdefault(day, []).append(slot_id)
        for day, slots in slot_day_groups.items():
            slots_sorted = sorted(slots, key=lambda s: self._slot_index.get(s, 10**9))
            for t_id in self._data.teachers:
                prev_occ = None
                for slot_idx, s_id in enumerate(slots_sorted):
                    occ = pulp.lpSum(x[key] for key in self._keys_by_teacher_slot.get((t_id, s_id), []))
                    if prev_occ is not None:
                        gap = pulp.LpVariable(
                            f"frag_{t_id}__{day}__{slot_idx}",
                            lowBound=0,
                            upBound=1,
                            cat=pulp.const.LpContinuous,
                        )
                        prob += gap >= occ - prev_occ
                        prob += gap >= prev_occ - occ
                        self._fragmentation_gap_vars[(t_id, s_id)] = gap
                    prev_occ = occ
    def _compute_feasible_keys(self) -> list[tuple[str, str, str, str, str]]:
        data = self._data
        keys: list[tuple[str, str, str, str, str]] = []
        teacher_slot_sets: dict[str, set[str]] = {tid: set(t.available_slots) for tid, t in data.teachers.items()}
        room_slot_sets: dict[str, set[str]] = {rid: set(r.available_slots) for rid, r in data.rooms.items()}
        for c_id, subj in data.subjects.items():
            for b_id in subj.batch_ids:
                matched_teacher = self._task_teacher_map.get((b_id, c_id))
                candidate_teachers = [matched_teacher] if matched_teacher else []
                task_keys_added = False
                for t_id in candidate_teachers:
                    if not t_id:
                        continue
                    teacher = data.teachers.get(t_id)
                    if teacher is None:
                        continue
                    if c_id.strip().lower() not in [s.strip().lower() for s in teacher.subject_expertise]:
                        continue
                    t_slots = teacher_slot_sets[t_id] - self._break_slots
                    for r_id, room in data.rooms.items():
                        if room.room_type.strip().lower() != subj.required_room_type.strip().lower():
                            continue
                        batch_sizes = [data.batches[bid].size for bid in subj.batch_ids if bid in data.batches]
                        required_capacity = max(batch_sizes) if batch_sizes else subj.min_batch_size
                        if room.capacity < required_capacity:
                            continue
                        common_slots = t_slots & room_slot_sets[r_id]
                        for s_id in common_slots:
                            keys.append((t_id, r_id, s_id, c_id, b_id))
                            task_keys_added = True
        return keys
    def _add_teacher_clash_constraints(
        self,
        prob: pulp.LpProblem,
        x: dict[tuple[str, str, str, str, str], pulp.LpVariable],
    ) -> None:
        data = self._data
        for t_id in data.teachers:
            for s_id in data.time_slots:
                relevant = [x[key] for key in self._keys_by_teacher_slot.get((t_id, s_id), [])]
                if len(relevant) > 1:
                    prob += pulp.lpSum(relevant) <= 1, f"teacher_clash_{t_id}_{s_id}"
    def _add_room_clash_constraints(
        self,
        prob: pulp.LpProblem,
        x: dict[tuple[str, str, str, str, str], pulp.LpVariable],
    ) -> None:
        data = self._data
        for r_id in data.rooms:
            for s_id in data.time_slots:
                relevant = [x[key] for key in self._keys_by_room_slot.get((r_id, s_id), [])]
                if len(relevant) > 1:
                    prob += pulp.lpSum(relevant) <= 1, f"room_clash_{r_id}_{s_id}"
    def _add_curriculum_fulfillment_constraints(
        self,
        prob: pulp.LpProblem,
        x: dict[tuple[str, str, str, str, str], pulp.LpVariable],
    ) -> None:
        data = self._data
        for c_id, subj in data.subjects.items():
            for b_id in subj.batch_ids:
                relevant = [
                    x[key]
                    for key in self._keys_by_subject.get(c_id, [])
                    if key[4] == b_id
                ]
                if not relevant:
                    prob += pulp.lpSum([0]) == subj.required_hours, f"curriculum_impossible_{c_id}_{b_id}"
                    continue
                prob += pulp.lpSum(relevant) == subj.required_hours, f"curriculum_{c_id}_{b_id}"

    def _add_teacher_workload_constraints(
        self,
        prob: pulp.LpProblem,
        x: dict[tuple[str, str, str, str, str], pulp.LpVariable],
    ) -> None:
        data = self._data
        for t_id, teacher in data.teachers.items():
            relevant = [x[key] for key in self._keys_by_teacher.get(t_id, [])]
            if relevant:
                prob += pulp.lpSum(relevant) <= teacher.max_hours, f"workload_{t_id}"
    def _add_batch_conflict_constraints(
        self,
        prob: pulp.LpProblem,
        x: dict[tuple[str, str, str, str, str], pulp.LpVariable],
    ) -> None:
        data = self._data
        for b_id in data.batches:
            for s_id in data.time_slots:
                relevant = [x[key] for key in self._keys_by_batch_slot.get((b_id, s_id), [])]
                if len(relevant) > 1:
                    prob += pulp.lpSum(relevant) <= 1, f"batch_conflict_{b_id}_{s_id}"

    def _add_batch_subject_day_constraints(
        self,
        prob: pulp.LpProblem,
        x: dict[tuple[str, str, str, str, str], pulp.LpVariable],
    ) -> None:
        for (b_id, c_id, day), keys in self._keys_by_batch_subject_day.items():
            if len(keys) > 1:
                prob += pulp.lpSum(x[key] for key in keys) <= 1, f"batch_subject_day_{b_id}_{c_id}_{day}"
    def _add_risk_hard_blocks(
        self,
        prob: pulp.LpProblem,
        x: dict[tuple[str, str, str, str, str], pulp.LpVariable],
    ) -> None:
        for key in self._feasible_keys:
            risk = self._data.risk_scores.get(key)
            if risk is None:
                t_id, r_id, s_id, c_id, b_id = key
                risk = self._data.risk_scores.get((t_id, r_id, s_id, c_id), 0.0)
            if risk >= 1.0:
                prob += x[key] == 0, f"hard_risk_block_{'__'.join(key)}"
    def _build_objective(
        self,
        x: dict[tuple[str, str, str, str, str], pulp.LpVariable],
        weights: dict[str, float],
    ) -> pulp.LpAffineExpression:
        data = self._data
        total_slots = max(len(data.time_slots), 1)
        satisfaction_terms: list[Any] = []
        utilisation_terms: list[Any] = []
        preference_terms: list[Any] = []
        risk_terms: list[Any] = []
        for key in self._feasible_keys:
            t_id, r_id, s_id, c_id, b_id = key
            var = x[key]
            pref_score = data.preference_scores.get((t_id, s_id), 0.5)
            satisfaction_terms.append(pref_score * var)
            utilisation_terms.append((1.0 / total_slots) * var)
            teacher = data.teachers[t_id]
            preference_terms.append((1.0 if s_id in teacher.preferred_slots else 0.0) * var)
            risk = data.risk_scores.get(key)
            if risk is None:
                risk = data.risk_scores.get((t_id, r_id, s_id, c_id), 0.0)
            risk_terms.append(risk * var)
        fragmentation_terms = list(self._fragmentation_gap_vars.values())

        objective = (
            weights["w_satisfaction"] * pulp.lpSum(satisfaction_terms)
            + weights["w_utilization"] * pulp.lpSum(utilisation_terms)
            + weights["w_preference"] * pulp.lpSum(preference_terms)
            - weights["w_risk"] * pulp.lpSum(risk_terms)
            - weights["w_fragmentation"] * pulp.lpSum(fragmentation_terms)
        )
        return objective
    def _add_no_good_cuts(
        self,
        prob: pulp.LpProblem,
        x: dict[tuple[str, str, str, str, str], pulp.LpVariable],
        previous_solutions: list[dict[tuple[str, str, str, str, str], int]],
    ) -> None:
        for sol_idx, prev_sol in enumerate(previous_solutions):
            active_keys = [key for key, val in prev_sol.items() if val == 1]
            if not active_keys:
                continue
            active_vars = [x[key] for key in active_keys if key in x]
            if not active_vars:
                continue
            prob += pulp.lpSum(active_vars) <= len(active_vars) - 1, f"no_good_cut_{sol_idx}"
        if previous_solutions:
            logger.debug("Added %d no good cut...", len(previous_solutions))
    def _build_explanation(
        self,
        variant_index: int,
        status: str,
        obj_value: float,
        assignments: list[Assignment],
        weights: dict[str, float],
    ) -> str:
        if not assignments:
            return (
                f"Variant {variant_index} could not find a feasible solution "
                f"(solver status: {status}).  The problem may be over constrained... "
                "consider relaxing teacher availability or adding more rooms."
            )
        total = len(assignments)
        high_risk = sum(1 for a in assignments if a.risk_score > 0.6)
        avg_risk = sum(a.risk_score for a in assignments) / max(total, 1)
        dominant_weight = max(weights, key=lambda k: weights[k])
        weight_desc = {
            "w_satisfaction": "student and teacher satisfaction",
            "w_utilization": "room utilisation",
            "w_preference": "teacher slot preferences",
            "w_risk": "disruption risk minimisation",
            "w_fragmentation": "schedule compactness",
        }.get(dominant_weight, dominant_weight)
        lines = [
            f"Variant {variant_index} , Solver:- {status}, Objective score:- {obj_value:.2f}.",
            f"Total classes scheduled: {total}.",
            f"Primary optimisation focus: {weight_desc}.",
            f"High risk assignments (risk > 0.6): {high_risk} ({100 * high_risk / max(total, 1):.1f}%).",
            f"Average risk score across all assignments: {avg_risk:.3f}.",
        ]
        if high_risk == 0:
            lines.append("No high risk slots were used , this variant has the most stable predicted schedule.")
        elif high_risk > total * 0.2:
            lines.append("A notable proportion of classes are in high risk slots. Consider whether the risk weight can be increased or if additional room/teacher capacity is needed.")
        return "  ".join(lines)
def run_optimizer(data: SchedulingInput) -> list[TimetableVariant]:
    logger.info("run_optimizer called....building TimetableOptimizer.")
    optimizer = TimetableOptimizer(data)
    variants = optimizer.generate_variants()
    logger.info("run_optimizer returning %d variant(s).", len(variants))
    return variants
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    time_labels = [
        "09:00","09:40","10:20","11:00","11:40",
        "12:20","13:00","13:40","14:20","15:00",
        "15:40","16:20","17:00","17:40","18:20"
    ]
    break_slots = [f"D{d}_12:20" for d in range(1, 6)]
    _slots = [f"D{d}_{t}" for d in range(1, 6) for t in time_labels]
    batches = {
        "B1A": Batch("B1A", "CS 1A", 60, 1, "CS"),
        "B1B": Batch("B1B", "CS 1B", 58, 1, "CS"),
        "B1C": Batch("B1C", "CS 1C", 62, 1, "CS"),
        "B1D": Batch("B1D", "CS 1D", 59, 1, "CS"),
        "B2A": Batch("B2A", "CS 2A", 55, 2, "CS"),
        "B2B": Batch("B2B", "CS 2B", 57, 2, "CS"),
        "B2C": Batch("B2C", "CS 2C", 53, 2, "CS"),
        "B2D": Batch("B2D", "CS 2D", 56, 2, "CS"),
        "B3A": Batch("B3A", "CS 3A", 48, 3, "CS"),
        "B3B": Batch("B3B", "CS 3B", 50, 3, "CS"),
        "B3C": Batch("B3C", "CS 3C", 47, 3, "CS"),
        "B3D": Batch("B3D", "CS 3D", 49, 3, "CS"),
        "B4A": Batch("B4A", "CS 4A", 42, 4, "CS"),
        "B4B": Batch("B4B", "CS 4B", 44, 4, "CS"),
        "B4C": Batch("B4C", "CS 4C", 41, 4, "CS"),
        "B4D": Batch("B4D", "CS 4D", 43, 4, "CS"),
    }
    teachers = {
    "T1": Teacher("T1", "Dr. Sharma", 50, _slots, ["S1","S8","S12"]),
    "T2": Teacher("T2", "Prof. Gupta", 50, _slots, ["S2","S9","S13"]),
    "T3": Teacher("T3", "Dr. Mehta", 50, _slots, ["S3","S10","S14"]),
    "T4": Teacher("T4", "Prof. Iyer", 50, _slots, ["S4","S7","S19","S23"]),
    "T5": Teacher("T5", "Dr. Khan", 50, _slots, ["S5","S11","S17","S22","S25","S29"]),
    "T6": Teacher("T6", "Prof. Roy", 50, _slots, ["S6","S15","S18","S26","S30"]),

    "T7": Teacher("T7", "Dr. Das", 50, _slots, ["S20","S24","S27"]),
    "T8": Teacher("T8", "Prof. Sen", 50, _slots, ["S1","S8","S12","S28"]),
    "T9": Teacher("T9", "Dr. Verma", 50, _slots, ["S1","S8"]),
    "T10": Teacher("T10", "Prof. Nair", 50, _slots, ["S2","S9","S13"]),
    
    "T11": Teacher("T11", "Dr. Reddy", 50, _slots, ["S3","S10","S19","S23","S25","S29"]),
    "T12": Teacher("T12", "Prof. Kulkarni", 50, _slots, ["S4","S7","S16","S21"]),
    "T13": Teacher("T13", "Dr. Banerjee", 50, _slots, ["S5","S11","S17","S22"]),
    "T14": Teacher("T14", "Prof. Chatterjee", 50, _slots, ["S6","S15","S18","S27"]),
    
    "T15": Teacher("T15", "Dr. Mukherjee", 50, _slots, ["S20","S24","S26","S30"]),
    "T16": Teacher("T16", "Prof. Bose", 50, _slots, ["S9","S28"]),
}

    rooms = {
        "R1": Room("R1", "LH 101", 120, "lecture", _slots),
        "R2": Room("R2", "LH 102", 120, "lecture", _slots),
        "R6": Room("R6", "LH 103", 120, "lecture", _slots),
        "R7": Room("R7", "LH 104", 120, "lecture", _slots),
        "R3": Room("R3", "Lab 201", 80, "lab", _slots),
        "R4": Room("R4", "Lab 202", 80, "lab", _slots),
        "R8": Room("R8", "Lab 203", 80, "lab", _slots),
        "R5": Room("R5", "Seminar Hall", 150, "seminar", _slots),
    }
    subjects = {


    # 1st Year (B1) → 6 Subjects + 1 Lab
    "S1": Subject("S1", "Mathematics I", 3, "CS", "lecture",
                  ["T1","T8","T9"], ["B1A","B1B","B1C","B1D"]),

    "S2": Subject("S2", "Physics", 3, "CS", "lecture",
                  ["T2","T10"], ["B1A","B1B","B1C","B1D"]),

    "S3": Subject("S3", "Basic Electronics", 3, "CS", "lecture",
                  ["T3","T11"], ["B1A","B1B","B1C","B1D"]),

    "S4": Subject("S4", "Programming Fundamentals", 3, "CS", "lecture",
                  ["T4","T12"], ["B1A","B1B","B1C","B1D"]),

    "S5": Subject("S5", "Engineering Mechanics", 3, "CS", "lecture",
                  ["T5","T13"], ["B1A","B1B","B1C","B1D"]),

    "S6": Subject("S6", "Communication Skills", 3, "CS", "lecture",
                  ["T6","T14"], ["B1A","B1B","B1C","B1D"]),

    "S7": Subject("S7", "Programming Lab", 3, "CS", "lab",
                  ["T4","T12"], ["B1A","B1B","B1C","B1D"], 30),


    # 2nd Year (B2) → 4 Subjects + 4 Labs
    "S8": Subject("S8", "Data Structures", 3, "CS", "lecture",
                  ["T1","T8","T9"], ["B2A","B2B","B2C","B2D"]),

    "S9": Subject("S9", "Operating Systems", 3, "CS", "lecture",
                  ["T2","T10"], ["B2A","B2B","B2C","B2D"]),

    "S10": Subject("S10", "Database Systems", 3, "CS", "lecture",
                   ["T3","T11"], ["B2A","B2B","B2C","B2D"]),

    "S11": Subject("S11", "Discrete Mathematics", 3, "CS", "lecture",
                   ["T5","T13"], ["B2A","B2B","B2C","B2D"]),

    "S12": Subject("S12", "DS Lab", 3, "CS", "lab",
                   ["T1","T8"], ["B2A","B2B","B2C","B2D"], 30),

    "S13": Subject("S13", "OS Lab", 3, "CS", "lab",
                   ["T2","T10"], ["B2A","B2B","B2C","B2D"], 30),

    "S14": Subject("S14", "DBMS Lab", 3, "CS", "lab",
                   ["T3","T11"], ["B2A","B2B","B2C","B2D"], 30),

    "S15": Subject("S15", "Linux Lab", 3, "CS", "lab",
                   ["T6","T14"], ["B2A","B2B","B2C","B2D"], 30),


    "S16": Subject("S16", "Computer Networks", 3, "CS", "lecture",
                   ["T3","T4","T12"], ["B3A","B3B","B3C","B3D"]),

    "S17": Subject("S17", "Software Engineering", 3, "CS", "lecture",
                   ["T5","T13"], ["B3A","B3B","B3C","B3D"]),

    "S18": Subject("S18", "Theory of Computation", 3, "CS", "lecture",
                   ["T6","T14"], ["B3A","B3B","B3C","B3D"]),

    "S19": Subject("S19", "Artificial Intelligence", 3, "CS", "lecture",
                   ["T4","T11"], ["B3A","B3B","B3C","B3D"]),

    "S20": Subject("S20", "Web Technologies", 3, "CS", "lecture",
                   ["T7","T15"], ["B3A","B3B","B3C","B3D"]),

    "S21": Subject("S21", "CN Lab", 3, "CS", "lab",
                   ["T3","T12"], ["B3A","B3B","B3C","B3D"], 30),

    "S22": Subject("S22", "SE Lab", 3, "CS", "lab",
                   ["T5","T13"], ["B3A","B3B","B3C","B3D"], 30),

    "S23": Subject("S23", "AI Lab", 3, "CS", "lab",
                   ["T4","T11"], ["B3A","B3B","B3C","B3D"], 30),

    "S24": Subject("S24", "Web Lab", 3, "CS", "lab",
                   ["T7","T15"], ["B3A","B3B","B3C","B3D"], 30),


    "S25": Subject("S25", "Machine Learning", 3, "CS", "lecture",
                   ["T5","T11"], ["B4A","B4B","B4C","B4D"]),

    "S26": Subject("S26", "Cloud Computing", 3, "CS", "lecture",
                   ["T6","T15"], ["B4A","B4B","B4C","B4D"]),

    "S27": Subject("S27", "Cyber Security", 3, "CS", "lecture",
                   ["T7","T14"], ["B4A","B4B","B4C","B4D"]),

    "S28": Subject("S28", "Big Data Analytics", 3, "CS", "lecture",
                   ["T8","T16"], ["B4A","B4B","B4C","B4D"]),

    "S29": Subject("S29", "ML Lab", 3, "CS", "lab",
                   ["T5","T11"], ["B4A","B4B","B4C","B4D"], 30),

    "S30": Subject("S30", "Cloud Lab", 3, "CS", "lab",
                   ["T6","T15"], ["B4A","B4B","B4C","B4D"], 30),
}
    _sample_input = SchedulingInput(
        teachers=teachers,
        rooms=rooms,
        subjects=subjects,
        batches=batches,
        time_slots=_slots,
        break_slots=break_slots,
        risk_scores={},
        preference_scores={}
    )
    results = run_optimizer(_sample_input)
    def _slot_sort_key(slot_id: str) -> tuple[int, str]:
        day = _slot_day(slot_id)
        day_num = int(day[1:]) if day.startswith("D") and day[1:].isdigit() else 999
        return day_num, _slot_time(slot_id)
    batch_order = list(batches.keys())
    for v in results:
        print(f"\nVariant {v.variant_index} | Score: {v.objective_score} | Feasible: {v.feasible}")
        print(f"Weights used: {v.weights_used}")
        print(v.explanation)
        assignments_by_batch: dict[str, list[Assignment]] = {bid: [] for bid in batch_order}
        for a in v.assignments:
            batch_id = a.batch_ids[0] if a.batch_ids else "UNKNOWN"
            assignments_by_batch.setdefault(batch_id, []).append(a)
        for batch_id in batch_order:
            batch_assignments = sorted(
                assignments_by_batch.get(batch_id, []),
                key=lambda a: (_slot_sort_key(a.slot_id), a.subject_name, a.teacher_name, a.room_name),
            )
            if not batch_assignments:
                continue
            print(f"\nTime Table for batch :- {batch_id}")
            print(f"{'Day':<6} {'Time Slot':<13} {'Subject':<25} {'Faculty Assigned':<22} {'Room':<16} {'Risk Score':<10}")
            print("-" * 110)
            for a in batch_assignments:
                day = _slot_day(a.slot_id)
                time_range = _format_slot_range(_slot_time(a.slot_id))
                print(
                    f"{day:<6} {time_range:<13} {a.subject_name:<25} {a.teacher_name:<22} {a.room_name:<16} {a.risk_score:<10.2f}"
                )