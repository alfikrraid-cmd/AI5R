const ALL = "ALL";

function normalized(value) {
  return String(value ?? "").trim().toLowerCase();
}

export function filterEquipment(equipment, filters) {
  const search = normalized(filters.search);

  return equipment.filter((item) => {
    const searchable = [
      item.equipment_id,
      item.tag_number,
      item.equipment_name,
      item.manufacturer,
      item.model,
    ].some((value) => normalized(value).includes(search));

    return (
      (!search || searchable) &&
      (filters.area === ALL || item.area === filters.area) &&
      (filters.equipmentType === ALL ||
        item.equipment_type === filters.equipmentType) &&
      (filters.status === ALL || item.status === filters.status)
    );
  });
}

export function equipmentFilterOptions(equipment, key) {
  return [...new Set(equipment.map((item) => item[key]).filter(Boolean))].sort();
}

export function equipmentStatusVariant(status) {
  const normalizedStatus = normalized(status);

  if (["active", "available", "operational"].includes(normalizedStatus)) {
    return "success";
  }

  if (["maintenance", "warning", "standby"].includes(normalizedStatus)) {
    return "warning";
  }

  if (["inactive", "fault", "out of service"].includes(normalizedStatus)) {
    return "danger";
  }

  return "info";
}
