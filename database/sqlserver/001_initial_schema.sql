/*
  UNKNOWN / TLC event platform
  SQL Server relational baseline
  Apply with a migration runner in a non-production database first.

  Deliberate choices:
  - uniqueidentifier keys avoid exposing sequential record counts;
  - UTC datetime2 timestamps;
  - answer keys are server-side data and must never be returned by public APIs;
  - media files live outside SQL Server; only metadata/object keys are stored here;
  - score_entry is an append-only ledger; corrections are compensating entries.
*/

CREATE SCHEMA competition;
GO

CREATE TABLE competition.event_edition (
    event_edition_id uniqueidentifier NOT NULL CONSTRAINT pk_event_edition PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    name nvarchar(160) NOT NULL,
    event_year smallint NOT NULL,
    status varchar(20) NOT NULL CONSTRAINT ck_event_edition_status CHECK (status IN ('DRAFT','ACTIVE','ARCHIVED')),
    starts_at datetime2(3) NULL,
    ends_at datetime2(3) NULL,
    created_at datetime2(3) NOT NULL CONSTRAINT df_event_edition_created_at DEFAULT SYSUTCDATETIME(),
    updated_at datetime2(3) NOT NULL CONSTRAINT df_event_edition_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT uq_event_edition_year UNIQUE (event_year),
    CONSTRAINT ck_event_edition_dates CHECK (ends_at IS NULL OR starts_at IS NULL OR ends_at >= starts_at)
);
GO

CREATE TABLE competition.class_track (
    class_track_id uniqueidentifier NOT NULL CONSTRAINT pk_class_track PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    event_edition_id uniqueidentifier NOT NULL,
    code varchar(8) NOT NULL,
    display_name nvarchar(80) NOT NULL,
    preferred_language varchar(40) NOT NULL,
    description nvarchar(500) NULL,
    sort_order tinyint NOT NULL CONSTRAINT df_class_track_sort_order DEFAULT 0,
    CONSTRAINT fk_class_track_edition FOREIGN KEY (event_edition_id) REFERENCES competition.event_edition(event_edition_id),
    CONSTRAINT uq_class_track_code UNIQUE (event_edition_id, code)
);
GO

CREATE TABLE competition.user_account (
    user_id uniqueidentifier NOT NULL CONSTRAINT pk_user_account PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    event_edition_id uniqueidentifier NULL,
    username nvarchar(80) NOT NULL,
    display_name nvarchar(160) NOT NULL,
    password_hash varbinary(256) NULL,
    is_active bit NOT NULL CONSTRAINT df_user_account_active DEFAULT 1,
    created_at datetime2(3) NOT NULL CONSTRAINT df_user_account_created_at DEFAULT SYSUTCDATETIME(),
    last_login_at datetime2(3) NULL,
    CONSTRAINT fk_user_account_edition FOREIGN KEY (event_edition_id) REFERENCES competition.event_edition(event_edition_id),
    CONSTRAINT uq_user_account_username UNIQUE (username)
);
GO

CREATE TABLE competition.role (
    role_code varchar(30) NOT NULL CONSTRAINT pk_role PRIMARY KEY,
    description nvarchar(200) NOT NULL
);
GO

CREATE TABLE competition.user_role (
    user_id uniqueidentifier NOT NULL,
    role_code varchar(30) NOT NULL,
    assigned_at datetime2(3) NOT NULL CONSTRAINT df_user_role_assigned_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_user_role PRIMARY KEY (user_id, role_code),
    CONSTRAINT fk_user_role_user FOREIGN KEY (user_id) REFERENCES competition.user_account(user_id),
    CONSTRAINT fk_user_role_role FOREIGN KEY (role_code) REFERENCES competition.role(role_code)
);
GO

CREATE TABLE competition.student (
    student_id uniqueidentifier NOT NULL CONSTRAINT pk_student PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    event_edition_id uniqueidentifier NOT NULL,
    display_name nvarchar(120) NOT NULL,
    student_reference nvarchar(80) NULL,
    photo_asset_id uniqueidentifier NULL,
    is_public bit NOT NULL CONSTRAINT df_student_public DEFAULT 1,
    created_at datetime2(3) NOT NULL CONSTRAINT df_student_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT fk_student_edition FOREIGN KEY (event_edition_id) REFERENCES competition.event_edition(event_edition_id),
    CONSTRAINT uq_student_reference UNIQUE (event_edition_id, student_reference)
);
GO

CREATE TABLE competition.team (
    team_id uniqueidentifier NOT NULL CONSTRAINT pk_team PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    event_edition_id uniqueidentifier NOT NULL,
    name nvarchar(120) NOT NULL,
    slogan nvarchar(240) NULL,
    team_type varchar(20) NOT NULL CONSTRAINT ck_team_type CHECK (team_type IN ('LEARNING','MIXED')),
    is_public bit NOT NULL CONSTRAINT df_team_public DEFAULT 1,
    created_at datetime2(3) NOT NULL CONSTRAINT df_team_created_at DEFAULT SYSUTCDATETIME(),
    updated_at datetime2(3) NOT NULL CONSTRAINT df_team_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT fk_team_edition FOREIGN KEY (event_edition_id) REFERENCES competition.event_edition(event_edition_id),
    CONSTRAINT uq_team_name_per_edition UNIQUE (event_edition_id, name)
);
GO

CREATE TABLE competition.team_class (
    team_id uniqueidentifier NOT NULL,
    class_track_id uniqueidentifier NOT NULL,
    CONSTRAINT pk_team_class PRIMARY KEY (team_id, class_track_id),
    CONSTRAINT fk_team_class_team FOREIGN KEY (team_id) REFERENCES competition.team(team_id),
    CONSTRAINT fk_team_class_class FOREIGN KEY (class_track_id) REFERENCES competition.class_track(class_track_id)
);
GO

CREATE TABLE competition.team_member (
    team_member_id uniqueidentifier NOT NULL CONSTRAINT pk_team_member PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    team_id uniqueidentifier NOT NULL,
    student_id uniqueidentifier NOT NULL,
    joined_at datetime2(3) NOT NULL CONSTRAINT df_team_member_joined_at DEFAULT SYSUTCDATETIME(),
    left_at datetime2(3) NULL,
    is_captain bit NOT NULL CONSTRAINT df_team_member_captain DEFAULT 0,
    CONSTRAINT fk_team_member_team FOREIGN KEY (team_id) REFERENCES competition.team(team_id),
    CONSTRAINT fk_team_member_student FOREIGN KEY (student_id) REFERENCES competition.student(student_id),
    CONSTRAINT ck_team_member_dates CHECK (left_at IS NULL OR left_at >= joined_at)
);
GO

CREATE UNIQUE INDEX ux_team_member_active ON competition.team_member(team_id, student_id) WHERE left_at IS NULL;
GO

CREATE TABLE competition.media_asset (
    media_asset_id uniqueidentifier NOT NULL CONSTRAINT pk_media_asset PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    uploaded_by_user_id uniqueidentifier NULL,
    asset_type varchar(30) NOT NULL CONSTRAINT ck_media_asset_type CHECK (asset_type IN ('LOGO','POSTER','PHOTO','SCREENSHOT','DOCUMENT','VIDEO','OTHER')),
    object_key nvarchar(500) NOT NULL,
    original_name nvarchar(255) NULL,
    mime_type varchar(120) NOT NULL,
    byte_length bigint NOT NULL CONSTRAINT ck_media_asset_length CHECK (byte_length >= 0),
    checksum_sha256 char(64) NULL,
    alt_text nvarchar(300) NULL,
    moderation_status varchar(20) NOT NULL CONSTRAINT ck_media_asset_moderation CHECK (moderation_status IN ('PENDING','APPROVED','REJECTED')),
    visibility varchar(20) NOT NULL CONSTRAINT ck_media_asset_visibility CHECK (visibility IN ('PRIVATE','PUBLIC')),
    created_at datetime2(3) NOT NULL CONSTRAINT df_media_asset_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT fk_media_asset_user FOREIGN KEY (uploaded_by_user_id) REFERENCES competition.user_account(user_id),
    CONSTRAINT uq_media_asset_object_key UNIQUE (object_key)
);
GO

ALTER TABLE competition.student ADD CONSTRAINT fk_student_photo FOREIGN KEY (photo_asset_id) REFERENCES competition.media_asset(media_asset_id);
GO

CREATE TABLE competition.team_media (
    team_id uniqueidentifier NOT NULL,
    media_asset_id uniqueidentifier NOT NULL,
    caption nvarchar(300) NULL,
    sort_order int NOT NULL CONSTRAINT df_team_media_sort_order DEFAULT 0,
    CONSTRAINT pk_team_media PRIMARY KEY (team_id, media_asset_id),
    CONSTRAINT fk_team_media_team FOREIGN KEY (team_id) REFERENCES competition.team(team_id),
    CONSTRAINT fk_team_media_asset FOREIGN KEY (media_asset_id) REFERENCES competition.media_asset(media_asset_id)
);
GO

CREATE TABLE competition.round (
    round_id uniqueidentifier NOT NULL CONSTRAINT pk_round PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    event_edition_id uniqueidentifier NOT NULL,
    round_number smallint NOT NULL,
    name nvarchar(160) NOT NULL,
    round_type varchar(30) NOT NULL CONSTRAINT ck_round_type CHECK (round_type IN ('MCQ','PRESENTATION','DEBUGGING','PROJECT','PROGRAMMING','OTHER')),
    status varchar(20) NOT NULL CONSTRAINT ck_round_status CHECK (status IN ('DRAFT','UPCOMING','ACTIVE','COMPLETED','LOCKED')),
    description nvarchar(1000) NULL,
    starts_at datetime2(3) NULL,
    ends_at datetime2(3) NULL,
    CONSTRAINT fk_round_edition FOREIGN KEY (event_edition_id) REFERENCES competition.event_edition(event_edition_id),
    CONSTRAINT uq_round_number UNIQUE (event_edition_id, round_number)
);
GO

CREATE TABLE competition.round_class (
    round_id uniqueidentifier NOT NULL,
    class_track_id uniqueidentifier NOT NULL,
    CONSTRAINT pk_round_class PRIMARY KEY (round_id, class_track_id),
    CONSTRAINT fk_round_class_round FOREIGN KEY (round_id) REFERENCES competition.round(round_id),
    CONSTRAINT fk_round_class_class FOREIGN KEY (class_track_id) REFERENCES competition.class_track(class_track_id)
);
GO

CREATE TABLE competition.team_round_entry (
    team_id uniqueidentifier NOT NULL,
    round_id uniqueidentifier NOT NULL,
    entry_status varchar(20) NOT NULL CONSTRAINT ck_team_round_entry_status CHECK (entry_status IN ('REGISTERED','SUBMITTED','JUDGED','WITHDRAWN')),
    submitted_at datetime2(3) NULL,
    CONSTRAINT pk_team_round_entry PRIMARY KEY (team_id, round_id),
    CONSTRAINT fk_team_round_entry_team FOREIGN KEY (team_id) REFERENCES competition.team(team_id),
    CONSTRAINT fk_team_round_entry_round FOREIGN KEY (round_id) REFERENCES competition.round(round_id)
);
GO

CREATE TABLE competition.submission (
    submission_id uniqueidentifier NOT NULL CONSTRAINT pk_submission PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    team_id uniqueidentifier NOT NULL,
    round_id uniqueidentifier NOT NULL,
    submission_type varchar(30) NOT NULL CONSTRAINT ck_submission_type CHECK (submission_type IN ('PRESENTATION','POSTER','PROJECT','DEBUGGING','PROGRAMMING','OTHER')),
    title nvarchar(200) NOT NULL,
    description nvarchar(max) NULL,
    external_url nvarchar(1000) NULL,
    status varchar(20) NOT NULL CONSTRAINT ck_submission_status CHECK (status IN ('DRAFT','SUBMITTED','APPROVED','REJECTED','JUDGED')),
    submitted_at datetime2(3) NULL,
    created_by_user_id uniqueidentifier NULL,
    created_at datetime2(3) NOT NULL CONSTRAINT df_submission_created_at DEFAULT SYSUTCDATETIME(),
    updated_at datetime2(3) NOT NULL CONSTRAINT df_submission_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT fk_submission_team FOREIGN KEY (team_id) REFERENCES competition.team(team_id),
    CONSTRAINT fk_submission_round FOREIGN KEY (round_id) REFERENCES competition.round(round_id),
    CONSTRAINT fk_submission_user FOREIGN KEY (created_by_user_id) REFERENCES competition.user_account(user_id)
);
GO

CREATE TABLE competition.submission_media (
    submission_id uniqueidentifier NOT NULL,
    media_asset_id uniqueidentifier NOT NULL,
    caption nvarchar(300) NULL,
    sort_order int NOT NULL CONSTRAINT df_submission_media_sort_order DEFAULT 0,
    CONSTRAINT pk_submission_media PRIMARY KEY (submission_id, media_asset_id),
    CONSTRAINT fk_submission_media_submission FOREIGN KEY (submission_id) REFERENCES competition.submission(submission_id),
    CONSTRAINT fk_submission_media_asset FOREIGN KEY (media_asset_id) REFERENCES competition.media_asset(media_asset_id)
);
GO

CREATE TABLE competition.evaluation_criterion (
    criterion_id uniqueidentifier NOT NULL CONSTRAINT pk_evaluation_criterion PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    round_id uniqueidentifier NOT NULL,
    name nvarchar(120) NOT NULL,
    max_points int NOT NULL,
    sort_order int NOT NULL CONSTRAINT df_evaluation_criterion_sort_order DEFAULT 0,
    CONSTRAINT fk_evaluation_criterion_round FOREIGN KEY (round_id) REFERENCES competition.round(round_id),
    CONSTRAINT ck_evaluation_criterion_points CHECK (max_points BETWEEN 1 AND 1000),
    CONSTRAINT uq_evaluation_criterion_name UNIQUE (round_id, name)
);
GO

CREATE TABLE competition.submission_evaluation (
    submission_evaluation_id uniqueidentifier NOT NULL CONSTRAINT pk_submission_evaluation PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    submission_id uniqueidentifier NOT NULL,
    criterion_id uniqueidentifier NOT NULL,
    evaluator_user_id uniqueidentifier NOT NULL,
    points_awarded int NOT NULL,
    feedback nvarchar(1000) NULL,
    evaluated_at datetime2(3) NOT NULL CONSTRAINT df_submission_evaluation_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT fk_submission_evaluation_submission FOREIGN KEY (submission_id) REFERENCES competition.submission(submission_id),
    CONSTRAINT fk_submission_evaluation_criterion FOREIGN KEY (criterion_id) REFERENCES competition.evaluation_criterion(criterion_id),
    CONSTRAINT fk_submission_evaluation_user FOREIGN KEY (evaluator_user_id) REFERENCES competition.user_account(user_id),
    CONSTRAINT uq_submission_evaluation_once UNIQUE (submission_id, criterion_id, evaluator_user_id),
    CONSTRAINT ck_submission_evaluation_points CHECK (points_awarded >= 0)
);
GO

CREATE TABLE competition.question (
    question_id uniqueidentifier NOT NULL CONSTRAINT pk_question PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    created_by_user_id uniqueidentifier NULL,
    question_type varchar(30) NOT NULL CONSTRAINT ck_question_type CHECK (question_type IN ('MCQ','RIDDLE','CODE','DEBUGGING','CONCEPTUAL','THEORY')),
    difficulty varchar(20) NOT NULL CONSTRAINT ck_question_difficulty CHECK (difficulty IN ('EASY','MEDIUM','HARD')), 
    preferred_language varchar(40) NULL,
    prompt nvarchar(max) NOT NULL,
    code_snippet nvarchar(max) NULL,
    explanation nvarchar(max) NULL,
    default_points int NOT NULL CONSTRAINT df_question_points DEFAULT 10,
    is_active bit NOT NULL CONSTRAINT df_question_active DEFAULT 1,
    created_at datetime2(3) NOT NULL CONSTRAINT df_question_created_at DEFAULT SYSUTCDATETIME(),
    updated_at datetime2(3) NOT NULL CONSTRAINT df_question_updated_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT fk_question_user FOREIGN KEY (created_by_user_id) REFERENCES competition.user_account(user_id),
    CONSTRAINT ck_question_points CHECK (default_points BETWEEN 1 AND 100)
);
GO

CREATE TABLE competition.question_option (
    question_option_id uniqueidentifier NOT NULL CONSTRAINT pk_question_option PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    question_id uniqueidentifier NOT NULL,
    option_key varchar(10) NOT NULL,
    option_text nvarchar(500) NOT NULL,
    is_correct bit NOT NULL CONSTRAINT df_question_option_correct DEFAULT 0,
    sort_order tinyint NOT NULL CONSTRAINT df_question_option_sort_order DEFAULT 0,
    CONSTRAINT fk_question_option_question FOREIGN KEY (question_id) REFERENCES competition.question(question_id),
    CONSTRAINT uq_question_option_key UNIQUE (question_id, option_key)
);
GO

CREATE TABLE competition.question_class (
    question_id uniqueidentifier NOT NULL,
    class_track_id uniqueidentifier NOT NULL,
    CONSTRAINT pk_question_class PRIMARY KEY (question_id, class_track_id),
    CONSTRAINT fk_question_class_question FOREIGN KEY (question_id) REFERENCES competition.question(question_id),
    CONSTRAINT fk_question_class_class FOREIGN KEY (class_track_id) REFERENCES competition.class_track(class_track_id)
);
GO

CREATE TABLE competition.question_tag (
    tag_code varchar(40) NOT NULL CONSTRAINT pk_question_tag PRIMARY KEY,
    description nvarchar(200) NULL
);
GO

CREATE TABLE competition.question_tag_link (
    question_id uniqueidentifier NOT NULL,
    tag_code varchar(40) NOT NULL,
    CONSTRAINT pk_question_tag_link PRIMARY KEY (question_id, tag_code),
    CONSTRAINT fk_question_tag_link_question FOREIGN KEY (question_id) REFERENCES competition.question(question_id),
    CONSTRAINT fk_question_tag_link_tag FOREIGN KEY (tag_code) REFERENCES competition.question_tag(tag_code)
);
GO

CREATE TABLE competition.quiz_blueprint (
    blueprint_id uniqueidentifier NOT NULL CONSTRAINT pk_quiz_blueprint PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    round_id uniqueidentifier NOT NULL,
    class_track_id uniqueidentifier NOT NULL,
    name nvarchar(160) NOT NULL,
    question_count int NOT NULL,
    seconds_per_question int NOT NULL CONSTRAINT df_blueprint_seconds DEFAULT 20,
    buzzer_enabled bit NOT NULL CONSTRAINT df_blueprint_buzzer DEFAULT 1,
    is_active bit NOT NULL CONSTRAINT df_blueprint_active DEFAULT 1,
    CONSTRAINT fk_blueprint_round FOREIGN KEY (round_id) REFERENCES competition.round(round_id),
    CONSTRAINT fk_blueprint_class FOREIGN KEY (class_track_id) REFERENCES competition.class_track(class_track_id),
    CONSTRAINT uq_blueprint_round_class UNIQUE (round_id, class_track_id),
    CONSTRAINT ck_blueprint_counts CHECK (question_count BETWEEN 1 AND 500 AND seconds_per_question BETWEEN 1 AND 3600)
);
GO

CREATE TABLE competition.quiz_distribution (
    distribution_id uniqueidentifier NOT NULL CONSTRAINT pk_quiz_distribution PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    blueprint_id uniqueidentifier NOT NULL,
    question_type varchar(30) NOT NULL,
    difficulty varchar(20) NULL,
    quantity int NOT NULL,
    CONSTRAINT fk_distribution_blueprint FOREIGN KEY (blueprint_id) REFERENCES competition.quiz_blueprint(blueprint_id),
    CONSTRAINT ck_distribution_quantity CHECK (quantity > 0)
);
GO

CREATE TABLE competition.quiz_session (
    quiz_session_id uniqueidentifier NOT NULL CONSTRAINT pk_quiz_session PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    blueprint_id uniqueidentifier NOT NULL,
    quiz_code varchar(32) NOT NULL,
    status varchar(20) NOT NULL CONSTRAINT ck_quiz_session_status CHECK (status IN ('WAITING','OPEN','ACTIVE','PAUSED','ENDED')),
    started_at datetime2(3) NULL,
    ended_at datetime2(3) NULL,
    created_at datetime2(3) NOT NULL CONSTRAINT df_quiz_session_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT fk_quiz_session_blueprint FOREIGN KEY (blueprint_id) REFERENCES competition.quiz_blueprint(blueprint_id),
    CONSTRAINT uq_quiz_session_code UNIQUE (quiz_code),
    CONSTRAINT ck_quiz_session_dates CHECK (ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at)
);
GO

CREATE TABLE competition.quiz_question (
    quiz_question_id uniqueidentifier NOT NULL CONSTRAINT pk_quiz_question PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    quiz_session_id uniqueidentifier NOT NULL,
    question_id uniqueidentifier NOT NULL,
    question_order int NOT NULL,
    prompt_snapshot nvarchar(max) NOT NULL,
    points_snapshot int NOT NULL,
    answer_key_snapshot nvarchar(max) NULL,
    opened_at datetime2(3) NULL,
    closed_at datetime2(3) NULL,
    CONSTRAINT fk_quiz_question_session FOREIGN KEY (quiz_session_id) REFERENCES competition.quiz_session(quiz_session_id),
    CONSTRAINT fk_quiz_question_question FOREIGN KEY (question_id) REFERENCES competition.question(question_id),
    CONSTRAINT uq_quiz_question_order UNIQUE (quiz_session_id, question_order),
    CONSTRAINT uq_quiz_question_once UNIQUE (quiz_session_id, question_id)
);
GO

CREATE TABLE competition.quiz_participant (
    participant_id uniqueidentifier NOT NULL CONSTRAINT pk_quiz_participant PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    quiz_session_id uniqueidentifier NOT NULL,
    team_id uniqueidentifier NOT NULL,
    joined_at datetime2(3) NOT NULL CONSTRAINT df_quiz_participant_joined_at DEFAULT SYSUTCDATETIME(),
    left_at datetime2(3) NULL,
    CONSTRAINT fk_quiz_participant_session FOREIGN KEY (quiz_session_id) REFERENCES competition.quiz_session(quiz_session_id),
    CONSTRAINT fk_quiz_participant_team FOREIGN KEY (team_id) REFERENCES competition.team(team_id),
    CONSTRAINT uq_quiz_participant_team UNIQUE (quiz_session_id, team_id)
);
GO

CREATE TABLE competition.buzzer_press (
    buzzer_press_id uniqueidentifier NOT NULL CONSTRAINT pk_buzzer_press PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    quiz_question_id uniqueidentifier NOT NULL,
    participant_id uniqueidentifier NOT NULL,
    pressed_at datetime2(3) NOT NULL CONSTRAINT df_buzzer_press_pressed_at DEFAULT SYSUTCDATETIME(),
    is_winner bit NOT NULL CONSTRAINT df_buzzer_press_winner DEFAULT 0,
    CONSTRAINT fk_buzzer_press_question FOREIGN KEY (quiz_question_id) REFERENCES competition.quiz_question(quiz_question_id),
    CONSTRAINT fk_buzzer_press_participant FOREIGN KEY (participant_id) REFERENCES competition.quiz_participant(participant_id)
);
GO

CREATE UNIQUE INDEX ux_buzzer_one_winner ON competition.buzzer_press(quiz_question_id) WHERE is_winner = 1;
GO

CREATE TABLE competition.answer_submission (
    answer_submission_id uniqueidentifier NOT NULL CONSTRAINT pk_answer_submission PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    quiz_question_id uniqueidentifier NOT NULL,
    participant_id uniqueidentifier NOT NULL,
    buzzer_press_id uniqueidentifier NULL,
    submitted_answer nvarchar(max) NOT NULL,
    is_final bit NOT NULL CONSTRAINT df_answer_submission_final DEFAULT 1,
    is_correct bit NULL,
    awarded_points int NOT NULL CONSTRAINT df_answer_submission_points DEFAULT 0,
    submitted_at datetime2(3) NOT NULL CONSTRAINT df_answer_submission_submitted_at DEFAULT SYSUTCDATETIME(),
    judged_at datetime2(3) NULL,
    judged_by_user_id uniqueidentifier NULL,
    CONSTRAINT fk_answer_question FOREIGN KEY (quiz_question_id) REFERENCES competition.quiz_question(quiz_question_id),
    CONSTRAINT fk_answer_participant FOREIGN KEY (participant_id) REFERENCES competition.quiz_participant(participant_id),
    CONSTRAINT fk_answer_buzzer FOREIGN KEY (buzzer_press_id) REFERENCES competition.buzzer_press(buzzer_press_id),
    CONSTRAINT fk_answer_judge FOREIGN KEY (judged_by_user_id) REFERENCES competition.user_account(user_id),
    CONSTRAINT ck_answer_points CHECK (awarded_points BETWEEN -100 AND 100)
);
GO

CREATE UNIQUE INDEX ux_answer_one_final ON competition.answer_submission(quiz_question_id, participant_id) WHERE is_final = 1;
GO

CREATE TABLE competition.score_entry (
    score_entry_id uniqueidentifier NOT NULL CONSTRAINT pk_score_entry PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    team_id uniqueidentifier NOT NULL,
    round_id uniqueidentifier NOT NULL,
    quiz_session_id uniqueidentifier NULL,
    answer_submission_id uniqueidentifier NULL,
    points_delta decimal(10,2) NOT NULL,
    reason varchar(40) NOT NULL CONSTRAINT ck_score_reason CHECK (reason IN ('ANSWER','PENALTY','BONUS','ADJUSTMENT','CORRECTION')),
    note nvarchar(500) NULL,
    created_by_user_id uniqueidentifier NULL,
    created_at datetime2(3) NOT NULL CONSTRAINT df_score_entry_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT fk_score_team FOREIGN KEY (team_id) REFERENCES competition.team(team_id),
    CONSTRAINT fk_score_round FOREIGN KEY (round_id) REFERENCES competition.round(round_id),
    CONSTRAINT fk_score_session FOREIGN KEY (quiz_session_id) REFERENCES competition.quiz_session(quiz_session_id),
    CONSTRAINT fk_score_answer FOREIGN KEY (answer_submission_id) REFERENCES competition.answer_submission(answer_submission_id),
    CONSTRAINT fk_score_user FOREIGN KEY (created_by_user_id) REFERENCES competition.user_account(user_id)
);
GO

CREATE TABLE competition.announcement (
    announcement_id uniqueidentifier NOT NULL CONSTRAINT pk_announcement PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    event_edition_id uniqueidentifier NOT NULL,
    title nvarchar(200) NOT NULL,
    body nvarchar(max) NOT NULL,
    severity varchar(20) NOT NULL CONSTRAINT ck_announcement_severity CHECK (severity IN ('NORMAL','IMPORTANT','URGENT')),
    published_at datetime2(3) NULL,
    created_by_user_id uniqueidentifier NULL,
    CONSTRAINT fk_announcement_edition FOREIGN KEY (event_edition_id) REFERENCES competition.event_edition(event_edition_id),
    CONSTRAINT fk_announcement_user FOREIGN KEY (created_by_user_id) REFERENCES competition.user_account(user_id)
);
GO

CREATE TABLE competition.schedule_item (
    schedule_item_id uniqueidentifier NOT NULL CONSTRAINT pk_schedule_item PRIMARY KEY DEFAULT NEWSEQUENTIALID(),
    event_edition_id uniqueidentifier NOT NULL,
    round_id uniqueidentifier NULL,
    title nvarchar(200) NOT NULL,
    starts_at datetime2(3) NOT NULL,
    ends_at datetime2(3) NULL,
    location nvarchar(200) NULL,
    CONSTRAINT fk_schedule_edition FOREIGN KEY (event_edition_id) REFERENCES competition.event_edition(event_edition_id),
    CONSTRAINT fk_schedule_round FOREIGN KEY (round_id) REFERENCES competition.round(round_id),
    CONSTRAINT ck_schedule_dates CHECK (ends_at IS NULL OR ends_at >= starts_at)
);
GO

CREATE TABLE competition.audit_log (
    audit_log_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT pk_audit_log PRIMARY KEY,
    event_edition_id uniqueidentifier NULL,
    actor_user_id uniqueidentifier NULL,
    action_code varchar(80) NOT NULL,
    entity_name varchar(80) NOT NULL,
    entity_id uniqueidentifier NULL,
    details_json nvarchar(max) NULL,
    created_at datetime2(3) NOT NULL CONSTRAINT df_audit_log_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT fk_audit_edition FOREIGN KEY (event_edition_id) REFERENCES competition.event_edition(event_edition_id),
    CONSTRAINT fk_audit_user FOREIGN KEY (actor_user_id) REFERENCES competition.user_account(user_id),
    CONSTRAINT ck_audit_json CHECK (details_json IS NULL OR ISJSON(details_json) = 1)
);
GO

CREATE INDEX ix_team_class_class ON competition.team_class(class_track_id, team_id);
CREATE INDEX ix_team_member_student ON competition.team_member(student_id, left_at);
CREATE INDEX ix_submission_team_round ON competition.submission(team_id, round_id, status);
CREATE INDEX ix_submission_media_asset ON competition.submission_media(media_asset_id);
CREATE INDEX ix_question_filter ON competition.question(is_active, question_type, difficulty, preferred_language);
CREATE INDEX ix_question_class_class ON competition.question_class(class_track_id, question_id);
CREATE INDEX ix_quiz_session_blueprint ON competition.quiz_session(blueprint_id, status);
CREATE INDEX ix_quiz_question_session ON competition.quiz_question(quiz_session_id, question_order);
CREATE INDEX ix_buzzer_question_time ON competition.buzzer_press(quiz_question_id, pressed_at);
CREATE INDEX ix_answer_question_time ON competition.answer_submission(quiz_question_id, submitted_at);
CREATE INDEX ix_score_team_round ON competition.score_entry(team_id, round_id, created_at);
CREATE INDEX ix_audit_entity ON competition.audit_log(entity_name, entity_id, created_at);
GO

INSERT INTO competition.role(role_code, description) VALUES
    ('SUPER_ADMIN', 'Full system administration'),
    ('ADMIN', 'Event and quiz administration'),
    ('TEACHER', 'Class and student oversight'),
    ('COMMITTEE', 'Competition operations and scoring'),
    ('MENTOR', 'Team mentoring'),
    ('STUDENT', 'Student/team participant');
GO
