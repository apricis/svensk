create table words (
	id integer primary key not null,
	basic_form text not null unique
);


create table verbs (
    imperativ text not null,
    presens text not null,
    preteritum text not null,
    supinum text not null,
    word_id integer not null,
    foreign key (word_id) references words(id),
    primary key (word_id)
);


create table nouns (
    article char(3) not null,
    sing_definite text not null,
    pl_definite text,
    pl_indefinite text,
    word_id integer not null,
    foreign key (word_id) references words(id),
    primary key (word_id)
);

create table languages (
    id integer primary key not null,
    code text,
    language text not null
);

INSERT INTO languages(id, language) VALUES (1, "engelska"), (2, "ukrainska"), (3, "ryska");

create table pos (
    id integer primary key not null,
    code text,
    name text not null
);

INSERT INTO pos(id, name) VALUES (1, 'verb'), (2, 'noun'), (3, 'adjective');

create table translations (
    translation text not null,
    word_id integer not null,
    language_id integer not null,
    pos_id integer not null,
    foreign key (word_id) references words(id),
    foreign key (pos_id) references pos(id),
    foreign key (language_id) references languages(id),
    primary key (translation, word_id, language_id)
);

CREATE TABLE "android_metadata" ("locale" TEXT DEFAULT 'en_US');
INSERT INTO "android_metadata" VALUES ('en_US');