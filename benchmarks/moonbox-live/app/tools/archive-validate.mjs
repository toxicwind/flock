import fs from "fs";
import path from "path";
import Ajv from "ajv";
import addFormats from "ajv-formats";

const ajv = new Ajv({ allErrors: true });
addFormats(ajv);

const base = "src/content/archives/collectables/designer-toys/pop-mart/the-monsters";
const schemas = {
  character: JSON.parse(
    fs.readFileSync("schema/character.schema.json", "utf8"),
  ),
  series: JSON.parse(fs.readFileSync("schema/series.schema.json", "utf8")),
  product: JSON.parse(fs.readFileSync("schema/product.schema.json", "utf8")),
};

const validate = (schema, data, file) => {
  const v = ajv.compile(schema);
  const ok = v(data);
  if (!ok) {
    console.error(`Validation failed for ${file}`);
    console.error(v.errors);
    process.exitCode = 1;
  }
};

const filesIn = (dir) =>
  fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => path.join(dir, f));

// characters
for (const file of filesIn(path.join(base, "characters"))) {
  const data = JSON.parse(fs.readFileSync(file, "utf8"));
  validate(schemas.character, data, file);
}

// series
for (const file of filesIn(path.join(base, "series"))) {
  const data = JSON.parse(fs.readFileSync(file, "utf8"));
  validate(schemas.series, data, file);
}

// products
const productIds = new Set();
const identityMap = new Map();
for (const file of filesIn(path.join(base, "products"))) {
  const data = JSON.parse(fs.readFileSync(file, "utf8"));
  validate(schemas.product, data, file);

  if (Array.isArray(data.form)) {
    console.error(`non-merge: form array in ${file}`);
    process.exitCode = 1;
  }
  if (data.size && Array.isArray(data.size.h)) {
    console.error(`non-merge: size array in ${file}`);
    process.exitCode = 1;
  }

  const recomputed = [
    data.brand,
    data.line,
    data.character,
    data.series,
    data.form,
  ];
  if (data.variant) recomputed.push(data.variant);
  if (data.size && data.size.h) recomputed.push(`${data.size.h}cm`);
  if (data.release_date) recomputed.push(data.release_date.replace(/-/g, ""));
  if (data.distribution && data.distribution.region_lock) {
    const code =
      (data.distribution.markets && data.distribution.markets[0]) || "xx";
    recomputed.push(`reg-${code.toLowerCase()}`);
  }
  const recomputedId = recomputed.join("--");
  if (recomputedId !== data.product_id) {
    console.error(`product_id mismatch in ${file}: expected ${recomputedId}`);
    process.exitCode = 1;
  }
  if (productIds.has(data.product_id)) {
    console.error(`Duplicate product_id ${data.product_id}`);
    process.exitCode = 1;
  }
  productIds.add(data.product_id);

  const identityKey = [
    data.brand,
    data.line,
    data.character,
    data.series,
    data.form,
    data.variant || "",
    data.size && data.size.h ? data.size.h : "",
    data.release_date || "",
    data.edition && data.edition.kind ? data.edition.kind : "",
  ].join("|");
  if (identityMap.has(identityKey)) {
    const prev = identityMap.get(identityKey);
    const bothUnlocked =
      !(prev.distribution && prev.distribution.region_lock) &&
      !(data.distribution && data.distribution.region_lock);
    if (bothUnlocked) {
      console.error(
        `region-split: ${file} and ${prev.file} differ only by markets`,
      );
      process.exitCode = 1;
    }
  } else {
    identityMap.set(identityKey, { file, distribution: data.distribution });
  }
}
