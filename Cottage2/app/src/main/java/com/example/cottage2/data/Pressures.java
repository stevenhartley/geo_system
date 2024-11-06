/**
 * SPDX-FileCopyrightText: 2023 Steven Hartley
 *
 * See the NOTICE file(s) distributed with this work for additional
 * information regarding copyright ownership.
 *
 * This program and the accompanying materials are made available under the
 * terms of the Apache License Version 2.0 which is available at
 * https://www.apache.org/licenses/LICENSE-2.0
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package com.example.cottage2.data;

import java.util.Arrays;
import java.util.Optional;

public enum Pressures {
    GEO_OUT(0, "GEO Out"),
    GEO_IN(1, "GEO In"),
    MAIN(2, "Main"),
    GEO_HEATING(3, "GEO Heating");

    private final Integer value;
    private final String name;
    private Pressures(Integer value, String name) {
        this.name = name;
        this.value = value;
    }

    public Integer getValue() {
        return this.value;
    }
    public String getName() {
        return this.name;
    }

    public static Optional<Pressures> from(Integer value) {
        return Arrays.stream(Pressures.values())
                .filter(p -> p.getValue().equals(value))
                .findAny();
    }
}
