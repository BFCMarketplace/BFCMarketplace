-- Two users A and B; B must never see or touch A's data.
insert into auth.users values ('aaaaaaaa-0000-0000-0000-000000000001'),('bbbbbbbb-0000-0000-0000-000000000002');

create or replace function pg_temp.assert(cond boolean, msg text) returns void language plpgsql as
$$ begin if not cond then raise exception 'ASSERT FAILED: %', msg; end if; end $$;

-- A creates a project
set role authenticated; set request.jwt.claim.sub = 'aaaaaaaa-0000-0000-0000-000000000001';
insert into projects(name,url,category,languages,countries) values ('InspectAI','https://inspectai.example','saas','{fr}','{FR}');
select pg_temp.assert((select count(*) from projects)=1, 'A sees own project');
select pg_temp.assert((select owner_id from projects limit 1)='aaaaaaaa-0000-0000-0000-000000000001', 'owner_id defaults to auth.uid()');
insert into activity_log(project_id, action) select id,'project.created' from projects;

-- A cannot forge another owner
do $$ begin
  begin insert into projects(owner_id,name,url) values ('bbbbbbbb-0000-0000-0000-000000000002','x','https://x.example');
    raise exception 'ASSERT FAILED: A inserted project for B';
  exception when insufficient_privilege then null; end;
end $$;

-- A cannot write api_usage (server only)
do $$ begin
  begin insert into api_usage(project_id,provider,operation) select id,'anthropic','t' from projects;
    raise exception 'ASSERT FAILED: user wrote api_usage';
  exception when insufficient_privilege then null; end;
end $$;

-- B sees nothing and cannot modify
reset role; set role authenticated; set request.jwt.claim.sub = 'bbbbbbbb-0000-0000-0000-000000000002';
select pg_temp.assert((select count(*) from projects)=0, 'B sees no projects');
select pg_temp.assert((select count(*) from activity_log)=0, 'B sees no activity');
update projects set name='hacked';
delete from projects;
do $$ begin
  begin insert into activity_log(project_id, action) values ((select id from projects limit 1), 'x');
  exception when others then null; end;
end $$;
do $$ begin
  begin
    -- direct insert into A's project by id must fail the RLS check
    execute 'insert into activity_log(project_id, action) values (''' || (select project_id from (select project_id from activity_log) s limit 1) || ''', ''x'')';
  exception when others then null; end;
end $$;

-- Back to A: data intact, B's attempts had no effect
reset role; set role authenticated; set request.jwt.claim.sub = 'aaaaaaaa-0000-0000-0000-000000000001';
select pg_temp.assert((select name from projects)='InspectAI', 'A project untouched by B');
select pg_temp.assert((select count(*) from activity_log)=1, 'A activity untouched by B');

-- Anonymous gets nothing
reset role; set role anon;
do $$ begin
  begin perform count(*) from projects; raise exception 'ASSERT FAILED: anon can read projects';
  exception when insufficient_privilege then null; end;
end $$;

-- Constraints
reset role; set role authenticated; set request.jwt.claim.sub = 'aaaaaaaa-0000-0000-0000-000000000001';
do $$ begin
  begin insert into projects(name,url) values ('bad','javascript:alert(1)');
    raise exception 'ASSERT FAILED: bad URL accepted';
  exception when check_violation then null; end;
end $$;
select pg_temp.assert(public.month_spend_eur((select id from projects))=0, 'month_spend starts at 0');
