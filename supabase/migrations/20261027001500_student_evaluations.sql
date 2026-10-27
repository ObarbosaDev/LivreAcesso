-- Avaliações individuais de desenvolvimento.
-- A nota nunca representa "normalidade" ou comparação entre estudantes:
-- representa uma observação contextualizada da evolução daquele estudante.
begin;

create table if not exists private.student_evaluations (
  id uuid primary key,
  student_id uuid not null references public.students(id),
  evaluator_id uuid not null references public.profiles(id),
  period_start date not null,
  period_end date not null,
  performance_score integer not null check (performance_score between 1 and 10),
  evolution_score integer not null check (evolution_score between 1 and 10),
  interaction_score integer not null check (interaction_score between 1 and 10),
  participation_score integer not null check (participation_score between 1 and 10),
  autonomy_score integer not null check (autonomy_score between 1 and 10),
  wellbeing_score integer not null check (wellbeing_score between 1 and 10),
  support_level text not null check (support_level in ('intenso', 'moderado', 'leve', 'independente')),
  observations text not null check (length(btrim(observations)) >= 10),
  effective_strategies text not null check (length(btrim(effective_strategies)) >= 10),
  next_objective text not null check (length(btrim(next_objective)) >= 10),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (period_end >= period_start),
  unique (student_id, period_start, period_end)
);

create index if not exists student_evaluations_student_period_idx
  on private.student_evaluations (student_id, period_end desc, created_at desc);

alter table private.student_evaluations enable row level security;
revoke all on private.student_evaluations from public, anon, authenticated;

create or replace function private.set_student_evaluation_updated_at()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists student_evaluations_set_updated_at on private.student_evaluations;
create trigger student_evaluations_set_updated_at
before update on private.student_evaluations
for each row execute function private.set_student_evaluation_updated_at();

create or replace function public.create_student_evaluation(
  p_evaluation_id uuid,
  p_student_id uuid,
  p_period_start date,
  p_period_end date,
  p_performance_score integer,
  p_evolution_score integer,
  p_interaction_score integer,
  p_participation_score integer,
  p_autonomy_score integer,
  p_wellbeing_score integer,
  p_support_level text,
  p_observations text,
  p_effective_strategies text,
  p_next_objective text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  inserted private.student_evaluations;
begin
  if not private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role, 'instructor'::public.user_role]) then
    raise exception using errcode = '42501', message = 'evaluation_forbidden';
  end if;

  insert into private.student_evaluations (
    id, student_id, evaluator_id, period_start, period_end,
    performance_score, evolution_score, interaction_score,
    participation_score, autonomy_score, wellbeing_score,
    support_level, observations, effective_strategies, next_objective
  ) values (
    p_evaluation_id, p_student_id, auth.uid(), p_period_start, p_period_end,
    p_performance_score, p_evolution_score, p_interaction_score,
    p_participation_score, p_autonomy_score, p_wellbeing_score,
    p_support_level, p_observations, p_effective_strategies, p_next_objective
  ) returning * into inserted;

  return jsonb_build_object(
    'id', inserted.id,
    'student_id', inserted.student_id,
    'evaluator_id', inserted.evaluator_id,
    'period_start', inserted.period_start,
    'period_end', inserted.period_end,
    'performance_score', inserted.performance_score,
    'evolution_score', inserted.evolution_score,
    'interaction_score', inserted.interaction_score,
    'participation_score', inserted.participation_score,
    'autonomy_score', inserted.autonomy_score,
    'wellbeing_score', inserted.wellbeing_score,
    'support_level', inserted.support_level,
    'observations', inserted.observations,
    'effective_strategies', inserted.effective_strategies,
    'next_objective', inserted.next_objective,
    'created_at', inserted.created_at,
    'updated_at', inserted.updated_at
  );
exception
  when unique_violation then
    raise exception using errcode = '23505', message = 'evaluation_period_already_exists';
end;
$$;

create or replace function public.list_student_evaluations(p_student_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role, 'instructor'::public.user_role, 'read_only'::public.user_role]) then
    raise exception using errcode = '42501', message = 'evaluation_forbidden';
  end if;

  return coalesce((select jsonb_agg(to_jsonb(item) order by item.period_end desc, item.created_at desc)
    from (select id, student_id, evaluator_id, period_start, period_end,
      performance_score, evolution_score, interaction_score, participation_score,
      autonomy_score, wellbeing_score, support_level, observations,
      effective_strategies, next_objective, created_at, updated_at
      from private.student_evaluations where student_id = p_student_id) item), '[]'::jsonb);
end;
$$;

revoke all on function public.create_student_evaluation(uuid, uuid, date, date, integer, integer, integer, integer, integer, integer, text, text, text, text) from public, anon;
grant execute on function public.create_student_evaluation(uuid, uuid, date, date, integer, integer, integer, integer, integer, integer, text, text, text, text) to authenticated;
revoke all on function public.list_student_evaluations(uuid) from public, anon;
grant execute on function public.list_student_evaluations(uuid) to authenticated;

commit;
