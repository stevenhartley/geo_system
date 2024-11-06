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
package com.example.cottage2;

import androidx.appcompat.app.AppCompatActivity;

import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.RadioGroup;

import com.example.cottage2.data.Mode;
import com.google.firebase.FirebaseApp;
import com.google.firebase.appcheck.FirebaseAppCheck;
import com.google.firebase.appcheck.debug.DebugAppCheckProviderFactory;
import com.google.firebase.database.DataSnapshot;
import com.google.firebase.database.DatabaseError;
import com.google.firebase.database.DatabaseReference;
import com.google.firebase.database.FirebaseDatabase;
import com.google.firebase.database.ValueEventListener;

import org.json.JSONObject;

public class OverrideActivity extends AppCompatActivity {

    private Button auto;
    private Button off;
    private Button geo;
    private Button electric;
    private Button geo_electric;
    private Button oil;

    private Button automatic;

    private RadioGroup buttonGroup;

    private EditText overrideTimeout;


    FirebaseDatabase firebaseDatabase;

    // creating a variable for our
    // Database Reference for Firebase.
    DatabaseReference databaseReference;

    private Mode mode = Mode.INVALID;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_override);

        buttonGroup = (RadioGroup)findViewById(R.id.idRadioGroup);

        FirebaseApp.initializeApp(/*context=*/ this);
        FirebaseAppCheck firebaseAppCheck = FirebaseAppCheck.getInstance();
        firebaseAppCheck.installAppCheckProviderFactory(
                DebugAppCheckProviderFactory.getInstance());

        firebaseDatabase = FirebaseDatabase.getInstance();

        // below line is used to get
        // reference for our database.
        databaseReference = firebaseDatabase.getReference("/cottage/geo/override");

        databaseReference.addListenerForSingleValueEvent(new ValueEventListener() {
            @Override
            public void onDataChange(DataSnapshot dataSnapshot) {
                try {

                    mode = Mode.fromValue((Integer)dataSnapshot.getValue()).orElse(Mode.AUTOMATIC);

                    switch (mode) {
                        case GEOTHERMAL:
                            buttonGroup.check(R.id.idButtonOverrideGeo);
                            break;
                        case OFF:
                            buttonGroup.check(R.id.idButtonOverrideOff);
                            break;
                        case GEO_ELECTRIC:
                            buttonGroup.check(R.id.idButtonOverrideGeoElectric);
                            break;
                        case ELECTRIC_OIL:
                            buttonGroup.check(R.id.idButtonOverrideOil);
                            break;
                        case ELECTRIC:
                            buttonGroup.check(R.id.idButtonOverrideElectric);
                        default:
                            buttonGroup.check(R.id.idButtonAutomatic);
                    }
                } catch (Exception e) {
                    Log.e("Error", e.toString());
                }

            }

            @Override
            public void onCancelled(DatabaseError databaseError) {
            }
        });

        overrideTimeout = (EditText) findViewById(R.id.idEditOverrideTimeout);

        off = (Button) findViewById(R.id.idButtonOverrideOff);
        off.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                mode = Mode.OFF;
                setOverride();
            }
        });

        electric = (Button) findViewById(R.id.idButtonOverrideElectric);
        electric.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                mode = Mode.ELECTRIC;
                setOverride();
            }
        });

        geo = (Button) findViewById(R.id.idButtonOverrideGeo);
        geo.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                mode = Mode.GEOTHERMAL;
                setOverride();
            }
        });

        oil = (Button) findViewById(R.id.idButtonOverrideOil);
        oil.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                mode = Mode.ELECTRIC_OIL;
                setOverride();
            }

        });

        automatic = (Button) findViewById(R.id.idButtonAutomatic);
        automatic.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                mode = Mode.AUTOMATIC;
                setOverride();
            }

        });

        geo_electric = (Button) findViewById(R.id.idButtonOverrideGeoElectric);
        geo_electric.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                mode = Mode.GEO_ELECTRIC;
                setOverride();
            }
        });

    }

    private void setOverride() {
        try {
            databaseReference.setValue(mode.getValue());
        }  catch (Exception e) {
            Log.e("Error", e.toString());
        }
    }



}